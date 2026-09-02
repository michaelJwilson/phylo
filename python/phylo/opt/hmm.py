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
from itertools import permutations
from pathlib import Path

import numpy as np
import torch
import yaml

from phylo.opt.constrain import free_from_log_simplex, log_simplex

# How far apart the emission rows start, in unconstrained units. Large
# enough to leave the stationary point, small enough not to preselect an
# answer: at 1.0 a state favours its symbol by a factor of e.
_SYMMETRY_BREAK = 1.0

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
    def _initial_slice(self) -> slice:
        return slice(0, self._n_states - 1)

    @property
    def _transition_slice(self) -> slice:
        start = self._n_states - 1
        return slice(start, start + self._n_states * (self._n_states - 1))

    @property
    def _emission_slice(self) -> slice:
        return slice(self._transition_slice.stop, self.n_parameters)

    @property
    def n_parameters(self) -> int:
        """Length of ``theta``: one free value per free probability."""
        return (
            (self._n_states - 1)
            + self._n_states * (self._n_states - 1)
            + self._n_states * (self._n_symbols - 1)
        )

    def initial(self) -> torch.Tensor:
        """A start that is uninformative but **not** symmetric.

        The uniform point -- every distribution uniform -- is a stationary
        point of the likelihood, not merely a poor guess: with all hidden
        states identical, the gradient with respect to the initial and
        transition parameters is exactly zero, and an optimizer started there
        stays there forever while the emission rows converge to the pooled
        symbol frequency. `tests/regression/test_opt_hmm.py` pins that.

        So the emission rows are tilted apart by a fixed amount, each state
        favouring a different symbol. Deterministic rather than random: a
        seeded jitter would make the fit depend on a second seed nobody
        declared.
        """
        theta = torch.zeros(self.n_parameters, dtype=self._dtype)
        free_emission = theta[self._emission_slice].reshape(
            self._n_states, self._n_symbols - 1
        )
        for state in range(self._n_states):
            free_emission[state, state % (self._n_symbols - 1)] = _SYMMETRY_BREAK
        return theta

    def constrain(self, theta: torch.Tensor) -> Mapping[str, torch.Tensor]:
        """Split ``theta`` into log initial, transition and emission matrices.

        Returned as *log* probabilities, which is what the forward recursion
        consumes; a caller comparing against truth exponentiates.
        """
        m, o = self._n_states, self._n_symbols
        return {
            "log_initial": log_simplex(theta[self._initial_slice]),
            "log_transition": log_simplex(
                theta[self._transition_slice].reshape(m, m - 1)
            ),
            "log_emission": log_simplex(theta[self._emission_slice].reshape(m, o - 1)),
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


def align_states(
    log_emission: torch.Tensor, reference: torch.Tensor
) -> tuple[int, ...]:
    """Permutation of fitted hidden states best matching ``reference``.

    The likelihood is invariant to relabelling the hidden states, so a fitted
    parameter set matches truth only up to a permutation and a recovery test
    has to choose one. Emissions are the discriminating signal -- two states
    with the same emission distribution are genuinely the same state -- so
    the permutation is the one minimizing total absolute emission
    difference, found by enumeration (``m!`` is small, and a greedy match can
    be wrong).

    Parameters
    ----------
    log_emission : torch.Tensor
        Fitted log emission matrix, shape ``(m, o)``.
    reference : torch.Tensor
        Emission matrix to align to, shape ``(m, o)``, as probabilities.

    Returns
    -------
    tuple[int, ...]
        ``order`` such that ``exp(log_emission)[list(order)]`` lines up with
        ``reference``.
    """
    emission = torch.exp(log_emission)
    best: tuple[int, ...] = ()
    best_cost = float("inf")
    for order in permutations(range(emission.shape[0])):
        cost = float((emission[list(order)] - reference).abs().sum())
        if cost < best_cost:
            best, best_cost = order, cost
    return best


def baum_welch(
    observations: np.ndarray,
    log_initial: torch.Tensor,
    log_transition: torch.Tensor,
    log_emission: torch.Tensor,
    max_iterations: int = 500,
    tolerance: float = 1e-12,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]:
    """Fit an HMM by expectation-maximization, with no autodiff involved.

    This is the point of having it: Baum-Welch is a genuinely independent
    fitting algorithm for the same model, so a gradient fit checked against
    it is checked against something other than itself. It shares no code with
    ``fit`` -- not the optimizer, not the parameterization (EM works directly
    in probabilities, with no unconstrained coordinates and no constraint
    map), only the model.

    Parameters
    ----------
    observations : np.ndarray
        Integer symbols, shape ``(n_sequences, sequence_length)``.
    log_initial, log_transition, log_emission : torch.Tensor
        Starting parameters, as log-probabilities.
    max_iterations : int
        Maximum EM iterations.
    tolerance : float
        Stop when the log-likelihood improves by less than this *relative*
        to its magnitude -- absolute would not transfer across data sizes
        (``DEV.md``, issue #111).

    Returns
    -------
    tuple[torch.Tensor, torch.Tensor, torch.Tensor, float]
        Fitted log initial, log transition and log emission, and the final
        log-likelihood.
    """
    data = torch.as_tensor(observations, dtype=torch.long)
    n_sequences, length = data.shape
    m, o = log_emission.shape
    emit = log_emission.t()

    previous = -float("inf")
    log_likelihood = previous
    for _ in range(max_iterations):
        # --- E step: forward and backward messages in log space ----------
        alpha = torch.empty((n_sequences, length, m), dtype=log_initial.dtype)
        alpha[:, 0] = log_initial.unsqueeze(0) + emit[data[:, 0]]
        for t in range(1, length):
            alpha[:, t] = (
                torch.logsumexp(
                    alpha[:, t - 1].unsqueeze(2) + log_transition.unsqueeze(0), dim=1
                )
                + emit[data[:, t]]
            )
        beta = torch.zeros((n_sequences, length, m), dtype=log_initial.dtype)
        for t in range(length - 2, -1, -1):
            beta[:, t] = torch.logsumexp(
                log_transition.unsqueeze(0)
                + (emit[data[:, t + 1]] + beta[:, t + 1]).unsqueeze(1),
                dim=2,
            )

        evidence = torch.logsumexp(alpha[:, -1], dim=1)
        log_likelihood = float(evidence.sum())

        gamma = alpha + beta - evidence[:, None, None]
        xi = (
            alpha[:, :-1].unsqueeze(3)
            + log_transition.unsqueeze(0).unsqueeze(0)
            + (emit[data[:, 1:]] + beta[:, 1:]).unsqueeze(2)
            - evidence[:, None, None, None]
        )

        # --- M step: normalized expected counts --------------------------
        log_initial = torch.logsumexp(gamma[:, 0], dim=0) - torch.log(
            torch.tensor(float(n_sequences), dtype=gamma.dtype)
        )
        transition_counts = torch.logsumexp(xi.reshape(-1, m, m), dim=0)
        log_transition = transition_counts - torch.logsumexp(
            transition_counts, dim=1, keepdim=True
        )
        symbol_mask = torch.nn.functional.one_hot(data.reshape(-1), o).to(gamma.dtype)
        weights = gamma.reshape(-1, m)
        emission_counts = torch.log(
            torch.exp(weights).t() @ symbol_mask + torch.finfo(gamma.dtype).tiny
        )
        log_emission = emission_counts - torch.logsumexp(
            emission_counts, dim=1, keepdim=True
        )
        emit = log_emission.t()

        if abs(log_likelihood - previous) <= tolerance * abs(log_likelihood):
            break
        previous = log_likelihood

    return log_initial, log_transition, log_emission, log_likelihood
