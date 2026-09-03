"""A 1-D Potts chain in an external field: reference instance of ``Objective``.

Not phylogenetics, and that is its job (issue #63). An interface justified by
a single model is shaped by that model; this one exists so the abstraction is
tested against something whose only similarity to a tree is that it is a
factorized distribution over discrete states.

The model, for ``q`` states on a chain of length ``L``::

    P(s) proportional to exp( J * sum_i delta(s_i, s_{i+1}) + sum_i h[s_i] )

with ``J`` a scalar coupling and ``h`` an external field. The normalizer is
computed exactly by transfer matrix in log space, which is the same
sum-product recursion Felsenstein pruning performs on a tree (Mezard &
Montanari, ch. 2; Koller & Friedman for the general framing) -- the reason
one optimizer is expected to serve both.

**Gauge.** The likelihood is invariant to adding a constant to every entry of
``h``, so ``h`` is fixed to ``logsumexp(h) == 0`` via
:func:`phylo.opt.constrain.log_simplex`. Without that the model is
unidentifiable and a fitted field has no value to compare against truth.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import torch
import yaml

from phylo.numerics import sample_rows
from phylo.opt.constrain import free_from_log_simplex, log_simplex

_REQUIRED_FIELDS = frozenset(
    {"seed", "n_chains", "chain_length", "n_states", "coupling", "field"}
)


@dataclass(frozen=True)
class PottsParams:
    """Fully-specified truth for a Potts-chain fixture.

    Parameters
    ----------
    n_states : int
        Number of states per site, >= 2.
    chain_length : int
        Sites per chain, >= 2. A length-1 chain has no coupling term and
        would leave ``J`` unidentifiable.
    n_chains : int
        Independent chains simulated from the truth.
    coupling : float
        The true ``J``.
    field : np.ndarray
        The true ``h``, shape ``(n_states,)``, canonicalized on load to
        ``logsumexp(h) == 0`` so it is comparable with a fitted field.
    seed : int
        Seed for ``np.random.default_rng``.
    """

    n_states: int
    chain_length: int
    n_chains: int
    coupling: float
    field: np.ndarray
    seed: int


def load_potts_params(path: Path) -> PottsParams:
    """Load and validate a Potts fixture yaml.

    Parameters
    ----------
    path : Path
        Path to the yaml file.

    Returns
    -------
    PottsParams
        Parsed truth, with ``field`` canonicalized to ``logsumexp(h) == 0``.

    Raises
    ------
    ValueError
        If a required field is missing, ``field`` does not have shape
        ``(n_states,)``, or a size is too small to identify the parameters.
    """
    raw = yaml.safe_load(path.read_text())

    missing = _REQUIRED_FIELDS - raw.keys()
    if missing:
        msg = f"{path}: missing required field(s) {sorted(missing)}"
        raise ValueError(msg)

    n_states = int(raw["n_states"])
    chain_length = int(raw["chain_length"])
    if n_states < 2:
        msg = f"{path}: n_states must be >= 2, got {n_states}"
        raise ValueError(msg)
    if chain_length < 2:
        msg = f"{path}: chain_length must be >= 2, got {chain_length}"
        raise ValueError(msg)

    field = np.asarray(raw["field"], dtype=np.float64)
    if field.shape != (n_states,):
        msg = f"{path}: field has shape {field.shape}, expected ({n_states},)"
        raise ValueError(msg)
    # Canonicalize the gauge here rather than demanding the yaml be written
    # in it: h and h + c are the same model, and a hand-written fixture
    # should not have to solve for c.
    field = field - float(np.log(np.exp(field).sum()))

    return PottsParams(
        n_states=n_states,
        chain_length=chain_length,
        n_chains=int(raw["n_chains"]),
        coupling=float(raw["coupling"]),
        field=field,
        seed=int(raw["seed"]),
    )


def log_partition(
    coupling: torch.Tensor, field: torch.Tensor, length: int
) -> torch.Tensor:
    """Exact ``log Z`` for a chain of ``length`` sites, by transfer matrix.

    Parameters
    ----------
    coupling : torch.Tensor
        Scalar ``J``.
    field : torch.Tensor
        ``h``, shape ``(q,)``.
    length : int
        Chain length, >= 1.

    Returns
    -------
    torch.Tensor
        Scalar ``log Z``, differentiable with respect to both parameters.
    """
    log_transfer = coupling * torch.eye(
        field.shape[0], dtype=field.dtype, device=field.device
    ) + field.unsqueeze(0)
    alpha = field
    for _ in range(length - 1):
        alpha = torch.logsumexp(alpha.unsqueeze(1) + log_transfer, dim=0)
    return torch.logsumexp(alpha, dim=0)


def simulate_chains(params: PottsParams) -> np.ndarray:
    """Draw ``n_chains`` exact samples from the truth in ``params``.

    Exact, not MCMC: the chain's backward messages give the conditional
    distributions directly, so the fixture carries no equilibration
    assumption (root ``CLAUDE.md``, "Simulate Component-Wise").

    Parameters
    ----------
    params : PottsParams
        The generating truth.

    Returns
    -------
    np.ndarray
        Integer states, shape ``(n_chains, chain_length)``.
    """
    rng = np.random.default_rng(params.seed)
    field = params.field
    log_transfer = params.coupling * np.eye(params.n_states) + field[np.newaxis, :]

    # backward[i] is the log weight of everything from site i+1 onward, given
    # the state at site i; backward[-1] is empty and so zero.
    backward = np.zeros((params.chain_length, params.n_states))
    for i in range(params.chain_length - 2, -1, -1):
        backward[i] = _logsumexp(log_transfer + backward[i + 1][np.newaxis, :], axis=1)

    chains = np.empty((params.n_chains, params.chain_length), dtype=np.int64)
    first = _softmax(field + backward[0])
    chains[:, 0] = rng.choice(params.n_states, size=params.n_chains, p=first)
    for i in range(1, params.chain_length):
        conditional = _softmax(log_transfer + backward[i][np.newaxis, :], axis=1)
        chains[:, i] = sample_rows(rng, conditional, chains[:, i - 1])
    return chains


class PottsObjective:
    """Negative log-likelihood of Potts chains, as an :class:`~phylo.opt.objective.Objective`.

    Parameters
    ----------
    chains : np.ndarray
        Observed states, shape ``(n_chains, chain_length)``.
    n_states : int
        Number of states, ``q``.
    dtype : torch.dtype
        Precision of the computation; ``float64`` by default, since a
        finite-difference derivative check is meaningless in ``float32``.
    """

    def __init__(
        self,
        chains: np.ndarray,
        n_states: int,
        dtype: torch.dtype = torch.float64,
    ) -> None:
        self._chains = torch.as_tensor(chains, dtype=torch.long)
        self._n_states = n_states
        self._dtype = dtype
        self._length = int(self._chains.shape[1])
        # Number of adjacent-pair agreements, per chain -- the only statistic
        # of the data the coupling sees, so it is computed once.
        self._agreements = (self._chains[:, :-1] == self._chains[:, 1:]).sum(dim=1)
        self._counts = torch.zeros(n_states, dtype=dtype)
        self._counts.scatter_add_(
            0, self._chains.reshape(-1), torch.ones(self._chains.numel(), dtype=dtype)
        )

    def initial(self) -> torch.Tensor:
        """A deliberately uninformative start: zero coupling, uniform field."""
        return torch.zeros(self._n_states, dtype=self._dtype)

    def constrain(self, theta: torch.Tensor) -> Mapping[str, torch.Tensor]:
        """Split ``theta`` into the coupling and the gauge-fixed field."""
        return {"coupling": theta[0], "field": log_simplex(theta[1:])}

    def __call__(self, theta: torch.Tensor) -> torch.Tensor:
        """Negative log-likelihood of every observed chain."""
        constrained = self.constrain(theta)
        coupling, field = constrained["coupling"], constrained["field"]
        log_z = log_partition(coupling, field, self._length)
        unnormalized = (
            coupling * self._agreements.to(self._dtype).sum()
            + (self._counts * field).sum()
        )
        return -(unnormalized - self._chains.shape[0] * log_z)

    def theta_from_truth(self, coupling: float, field: np.ndarray) -> torch.Tensor:
        """Place a known truth in the unconstrained coordinates.

        Parameters
        ----------
        coupling : float
            True ``J``.
        field : np.ndarray
            True ``h``, already gauge-fixed to ``logsumexp(h) == 0``.

        Returns
        -------
        torch.Tensor
            ``theta`` such that ``constrain(theta)`` returns this truth.
        """
        as_tensor = torch.as_tensor(field, dtype=self._dtype)
        return torch.cat(
            [
                torch.tensor([coupling], dtype=self._dtype),
                free_from_log_simplex(as_tensor),
            ]
        )


def _logsumexp(values: np.ndarray, axis: int) -> np.ndarray:
    peak = values.max(axis=axis, keepdims=True)
    total = peak + np.log(np.exp(values - peak).sum(axis=axis, keepdims=True))
    result: np.ndarray = total.squeeze(axis)
    return result


def _softmax(values: np.ndarray, axis: int = -1) -> np.ndarray:
    shifted = values - values.max(axis=axis, keepdims=True)
    weights = np.exp(shifted)
    result: np.ndarray = weights / weights.sum(axis=axis, keepdims=True)
    return result
