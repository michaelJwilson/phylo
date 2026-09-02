"""A discrete HMM: the second reference instance of ``Objective``.

Chosen over a second tree-like model for two reasons. It is one of issue
#63's named cases, and unlike the Potts chain it has an *independent fitting
algorithm* -- Baum-Welch -- so a gradient fit can be checked against
something other than itself (that check lands with the optimizer; this module
supplies the model it will be run on).

The forward recursion here and Felsenstein pruning are the same sum-product
computation on different graphs: a caterpillar tree carrying one observed
leaf per internal node *is* an HMM (Durbin et al., ch. 3; Koller & Friedman
for the general framing). The abstraction is expected to hold because the
three instances are one marginalization over three structures, not three
unrelated models sharing an optimizer.

**Label switching.** The likelihood is invariant to permuting the hidden
states, so a fitted parameter set matches truth only up to a permutation. The
model is otherwise identifiable; every row is gauge-fixed by
:func:`phylo.opt.constrain.log_simplex`. A recovery test must align the
permutation before comparing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import yaml

from phylo.opt.constrain import free_from_log_simplex, log_simplex

_REQUIRED_FIELDS = frozenset(
    {
        "seed",
        "n_sequences",
        "sequence_length",
        "n_states",
        "n_symbols",
        "initial",
        "transition",
        "emission",
    }
)


@dataclass(frozen=True)
class HmmParams:
    """Fully-specified truth for an HMM fixture.

    Parameters
    ----------
    n_states : int
        Hidden states, >= 2.
    n_symbols : int
        Emission alphabet size, >= 2.
    sequence_length : int
        Observations per sequence, >= 2. A length-1 sequence carries no
        transition and would leave the transition matrix unidentifiable.
    n_sequences : int
        Independent sequences simulated from the truth.
    initial : np.ndarray
        True initial distribution, shape ``(n_states,)``.
    transition : np.ndarray
        True transition matrix, shape ``(n_states, n_states)``, rows summing
        to 1.
    emission : np.ndarray
        True emission matrix, shape ``(n_states, n_symbols)``, rows summing
        to 1.
    seed : int
        Seed for ``np.random.default_rng``.
    """

    n_states: int
    n_symbols: int
    sequence_length: int
    n_sequences: int
    initial: np.ndarray
    transition: np.ndarray
    emission: np.ndarray
    seed: int


def load_hmm_params(path: Path) -> HmmParams:
    """Load and validate an HMM fixture yaml.

    Parameters
    ----------
    path : Path
        Path to the yaml file.

    Returns
    -------
    HmmParams
        The parsed, validated truth.

    Raises
    ------
    ValueError
        If a required field is missing, a size is too small to identify the
        parameters, or a distribution has the wrong shape or does not sum
        to 1.
    """
    raw = yaml.safe_load(path.read_text())

    missing = _REQUIRED_FIELDS - raw.keys()
    if missing:
        msg = f"{path}: missing required field(s) {sorted(missing)}"
        raise ValueError(msg)

    n_states = int(raw["n_states"])
    n_symbols = int(raw["n_symbols"])
    sequence_length = int(raw["sequence_length"])
    if n_states < 2:
        msg = f"{path}: n_states must be >= 2, got {n_states}"
        raise ValueError(msg)
    if n_symbols < 2:
        msg = f"{path}: n_symbols must be >= 2, got {n_symbols}"
        raise ValueError(msg)
    if sequence_length < 2:
        msg = f"{path}: sequence_length must be >= 2, got {sequence_length}"
        raise ValueError(msg)

    initial = _stochastic(raw["initial"], (n_states,), path, "initial")
    transition = _stochastic(
        raw["transition"], (n_states, n_states), path, "transition"
    )
    emission = _stochastic(raw["emission"], (n_states, n_symbols), path, "emission")

    return HmmParams(
        n_states=n_states,
        n_symbols=n_symbols,
        sequence_length=sequence_length,
        n_sequences=int(raw["n_sequences"]),
        initial=initial,
        transition=transition,
        emission=emission,
        seed=int(raw["seed"]),
    )


def _stochastic(
    raw: object, shape: tuple[int, ...], path: Path, name: str
) -> np.ndarray:
    values = np.asarray(raw, dtype=np.float64)
    if values.shape != shape:
        msg = f"{path}: {name} has shape {values.shape}, expected {shape}"
        raise ValueError(msg)
    sums = values.sum(axis=-1)
    if not np.allclose(sums, 1.0):
        msg = f"{path}: {name} rows sum to {sums.tolist()}, expected 1.0"
        raise ValueError(msg)
    return values


def simulate_sequences(params: HmmParams) -> np.ndarray:
    """Draw observation sequences by ancestral sampling from the truth.

    Parameters
    ----------
    params : HmmParams
        The generating truth.

    Returns
    -------
    np.ndarray
        Integer observations, shape ``(n_sequences, sequence_length)``.
    """
    rng = np.random.default_rng(params.seed)
    observations = np.empty(
        (params.n_sequences, params.sequence_length), dtype=np.int64
    )
    states = rng.choice(params.n_states, size=params.n_sequences, p=params.initial)
    observations[:, 0] = _sample_rows(rng, params.emission, states)
    for t in range(1, params.sequence_length):
        states = _sample_rows(rng, params.transition, states)
        observations[:, t] = _sample_rows(rng, params.emission, states)
    return observations


class HmmObjective:
    """Negative log-likelihood of observed sequences, by the forward algorithm.

    Parameters
    ----------
    observations : np.ndarray
        Observed symbols, shape ``(n_sequences, sequence_length)``.
    n_states : int
        Hidden states.
    n_symbols : int
        Emission alphabet size.
    dtype : torch.dtype
        Precision of the computation; ``float64`` by default, since a
        finite-difference derivative check is meaningless in ``float32``.
    """

    def __init__(
        self,
        observations: np.ndarray,
        n_states: int,
        n_symbols: int,
        dtype: torch.dtype = torch.float64,
    ) -> None:
        self._observations = torch.as_tensor(observations, dtype=torch.long)
        self._n_states = n_states
        self._n_symbols = n_symbols
        self._dtype = dtype

    @property
    def n_parameters(self) -> int:
        """Length of ``theta``: one free value per free probability."""
        return (
            (self._n_states - 1)
            + self._n_states * (self._n_states - 1)
            + self._n_states * (self._n_symbols - 1)
        )

    def initial(self) -> torch.Tensor:
        """A deliberately uninformative start: every distribution uniform."""
        return torch.zeros(self.n_parameters, dtype=self._dtype)

    def constrain(self, theta: torch.Tensor) -> Mapping[str, torch.Tensor]:
        """Split ``theta`` into log initial, transition and emission matrices.

        Returned as *log* probabilities, which is what the forward recursion
        consumes; a caller comparing against truth exponentiates.
        """
        m, o = self._n_states, self._n_symbols
        cut_initial = m - 1
        cut_transition = cut_initial + m * (m - 1)
        return {
            "log_initial": log_simplex(theta[:cut_initial]),
            "log_transition": log_simplex(
                theta[cut_initial:cut_transition].reshape(m, m - 1)
            ),
            "log_emission": log_simplex(theta[cut_transition:].reshape(m, o - 1)),
        }

    def __call__(self, theta: torch.Tensor) -> torch.Tensor:
        """Negative log-likelihood of every observed sequence."""
        constrained = self.constrain(theta)
        return -forward_log_likelihood(
            self._observations,
            constrained["log_initial"],
            constrained["log_transition"],
            constrained["log_emission"],
        )

    def theta_from_truth(
        self, initial: np.ndarray, transition: np.ndarray, emission: np.ndarray
    ) -> torch.Tensor:
        """Place a known truth in the unconstrained coordinates.

        Parameters
        ----------
        initial : np.ndarray
            True initial distribution, shape ``(n_states,)``.
        transition : np.ndarray
            True transition matrix, shape ``(n_states, n_states)``.
        emission : np.ndarray
            True emission matrix, shape ``(n_states, n_symbols)``.

        Returns
        -------
        torch.Tensor
            ``theta`` such that ``constrain(theta)`` returns this truth.
        """
        parts = [
            free_from_log_simplex(torch.log(torch.as_tensor(part, dtype=self._dtype)))
            for part in (initial, transition, emission)
        ]
        return torch.cat([parts[0], parts[1].reshape(-1), parts[2].reshape(-1)])


def forward_log_likelihood(
    observations: torch.Tensor,
    log_initial: torch.Tensor,
    log_transition: torch.Tensor,
    log_emission: torch.Tensor,
) -> torch.Tensor:
    """Total log-likelihood of ``observations`` by the forward recursion.

    Parameters
    ----------
    observations : torch.Tensor
        Integer symbols, shape ``(n_sequences, sequence_length)``.
    log_initial : torch.Tensor
        Log initial distribution, shape ``(m,)``.
    log_transition : torch.Tensor
        Log transition matrix, shape ``(m, m)``.
    log_emission : torch.Tensor
        Log emission matrix, shape ``(m, o)``.

    Returns
    -------
    torch.Tensor
        Scalar: the summed log-likelihood over sequences, differentiable
        with respect to every parameter.
    """
    emit = log_emission.t()
    alpha = log_initial.unsqueeze(0) + emit[observations[:, 0]]
    for t in range(1, observations.shape[1]):
        alpha = (
            torch.logsumexp(alpha.unsqueeze(2) + log_transition.unsqueeze(0), dim=1)
            + emit[observations[:, t]]
        )
    return torch.logsumexp(alpha, dim=1).sum()


def _sample_rows(
    rng: np.random.Generator, distributions: np.ndarray, rows: np.ndarray
) -> np.ndarray:
    """Draw one index per entry of ``rows`` from the row it selects."""
    cumulative = distributions[rows].cumsum(axis=1)
    draws = rng.random((rows.shape[0], 1))
    result: np.ndarray = (draws > cumulative).sum(axis=1)
    return result
