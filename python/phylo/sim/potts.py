"""``k``-state Potts model simulation on a general graph (issue #170).

``phylo.sim.graph.PottsGraph`` describes the model; this module draws spin
configurations from it, given an external field ``h`` shared by every node::

    P(s) proportional to exp( sum_{(i,j)} J_ij * delta(s_i, s_j) + sum_i h[s_i] )

An open 1-D chain (:func:`~phylo.sim.graph.is_open_chain`) has an exact O(L)
sampler by backward message passing -- the same recursion moved here from
``phylo.opt.potts.simulate_chains`` (issue #170's ``N = 1`` case), so it
carries no equilibration assumption. Every other graph -- a periodic ring, or
``ndim >= 2`` -- is sampled by single-site Gibbs/heat-bath MCMC: no exact
sampler is available in general, since the partition function itself is
already the enumeration this module is validated against at small sizes
(Mezard & Montanari, ch. 3, on Monte Carlo sampling of graphical models).

**Gauge.** As in ``phylo.opt.potts``, ``h`` is invariant to adding a constant
to every entry, so :func:`load_potts_lattice_params` canonicalizes it to
``logsumexp(h) == 0``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from phylo.numerics import sample_rows
from phylo.sim.graph import BoundaryCondition, PottsGraph, is_open_chain

_REQUIRED_FIELDS = frozenset(
    {
        "seed",
        "n_chains",
        "n_states",
        "shape",
        "boundary",
        "coupling",
        "field",
        "burn_in",
        "sweeps",
        "thin",
    }
)


@dataclass(frozen=True)
class PottsLatticeParams:
    """Fully-specified truth for a Potts-lattice/graph fixture.

    The graph is not stored directly -- it is rebuilt from ``shape``,
    ``boundary`` and ``coupling`` via :func:`~phylo.sim.graph.lattice_graph`,
    so the yaml retains exactly the parameters that produce it rather than a
    derived structure.

    Parameters
    ----------
    n_states : int
        Number of states per site, >= 2.
    shape : tuple[int, ...]
        Lattice shape passed to ``lattice_graph``.
    boundary : BoundaryCondition
        Boundary condition passed to ``lattice_graph``.
    coupling : float
        Scalar ``J`` shared by every edge.
    field : np.ndarray
        The true ``h``, shape ``(n_states,)``, canonicalized on load to
        ``logsumexp(h) == 0``.
    n_chains : int
        Independent Markov chains simulated.
    burn_in : int
        Gibbs sweeps discarded before recording (general graphs only; the
        exact 1-D chain sampler ignores this).
    sweeps : int
        Recorded samples per chain after burn-in (general graphs only).
    thin : int
        Gibbs sweeps between consecutive recorded samples within a chain
        (general graphs only); total sweeps run per chain is
        ``burn_in + sweeps * thin``.
    seed : int
        Seed for ``np.random.default_rng``.
    """

    n_states: int
    shape: tuple[int, ...]
    boundary: BoundaryCondition
    coupling: float
    field: np.ndarray
    n_chains: int
    burn_in: int
    sweeps: int
    thin: int
    seed: int


def load_potts_lattice_params(path: Path) -> PottsLatticeParams:
    """Load and validate a Potts-lattice fixture yaml.

    Parameters
    ----------
    path : Path
        Path to the yaml file.

    Returns
    -------
    PottsLatticeParams
        Parsed truth, with ``field`` canonicalized to ``logsumexp(h) == 0``.

    Raises
    ------
    ValueError
        If a required field is missing, ``field`` does not have shape
        ``(n_states,)``, ``boundary`` is not ``"open"``/``"periodic"``, or a
        size is too small to define the model (root ``CLAUDE.md``, "Do not
        introduce silent behaviour changes" -- every knob above is required,
        none defaults silently).
    """
    raw = yaml.safe_load(path.read_text())

    missing = _REQUIRED_FIELDS - raw.keys()
    if missing:
        msg = f"{path}: missing required field(s) {sorted(missing)}"
        raise ValueError(msg)

    n_states = int(raw["n_states"])
    if n_states < 2:
        msg = f"{path}: n_states must be >= 2, got {n_states}"
        raise ValueError(msg)

    shape = tuple(int(extent) for extent in raw["shape"])
    if not shape:
        msg = f"{path}: shape must have at least one dimension"
        raise ValueError(msg)

    boundary_raw = str(raw["boundary"])
    try:
        boundary = BoundaryCondition(boundary_raw)
    except ValueError as exc:
        msg = (
            f"{path}: boundary must be one of "
            f"{sorted(b.value for b in BoundaryCondition)}, got {boundary_raw!r}"
        )
        raise ValueError(msg) from exc

    field = np.asarray(raw["field"], dtype=np.float64)
    if field.shape != (n_states,):
        msg = f"{path}: field has shape {field.shape}, expected ({n_states},)"
        raise ValueError(msg)
    # Canonicalize the gauge here, as phylo.opt.potts.load_potts_params does:
    # h and h + c are the same model, and a hand-written fixture should not
    # have to solve for c.
    field = field - float(np.log(np.exp(field).sum()))

    n_chains = int(raw["n_chains"])
    burn_in = int(raw["burn_in"])
    sweeps = int(raw["sweeps"])
    thin = int(raw["thin"])
    if n_chains < 1:
        msg = f"{path}: n_chains must be >= 1, got {n_chains}"
        raise ValueError(msg)
    if burn_in < 0:
        msg = f"{path}: burn_in must be >= 0, got {burn_in}"
        raise ValueError(msg)
    if sweeps < 1:
        msg = f"{path}: sweeps must be >= 1, got {sweeps}"
        raise ValueError(msg)
    if thin < 1:
        msg = f"{path}: thin must be >= 1, got {thin}"
        raise ValueError(msg)

    return PottsLatticeParams(
        n_states=n_states,
        shape=shape,
        boundary=boundary,
        coupling=float(raw["coupling"]),
        field=field,
        n_chains=n_chains,
        burn_in=burn_in,
        sweeps=sweeps,
        thin=thin,
        seed=int(raw["seed"]),
    )


def simulate_potts(
    graph: PottsGraph, h: np.ndarray, seed: int, params: PottsLatticeParams
) -> np.ndarray:
    """Draw samples from the ``k``-state Potts model on ``graph``.

    Parameters
    ----------
    graph : PottsGraph
        The graph to sample on. Its per-edge ``coupling`` and (for dispatch)
        ``shape``/``boundary`` describe the model together with ``h``.
    h : np.ndarray
        External field, shape ``(n_states,)``, added at every node.
    seed : int
        Seed for ``np.random.default_rng``.
    params : PottsLatticeParams
        ``n_chains`` is used on every path; ``burn_in``, ``sweeps`` and
        ``thin`` are used only when ``graph`` is not an open 1-D chain.

    Returns
    -------
    np.ndarray
        Integer states, entries in ``[0, n_states)``. Shape
        ``(n_chains, graph.n_nodes)`` on the exact 1-D chain path -- one
        exact sample per chain, no equilibration. Shape
        ``(n_chains * sweeps, graph.n_nodes)`` on the general Gibbs path,
        chain-major: ``.reshape(n_chains, sweeps, graph.n_nodes)`` recovers
        each chain's ``sweeps`` samples, thinned by ``params.thin`` sweeps
        apart after ``params.burn_in`` discarded sweeps.
    """
    n_states = h.shape[0]
    if is_open_chain(graph):
        return _simulate_open_chain(graph, h, seed, params.n_chains, n_states)
    return _simulate_by_gibbs(graph, h, seed, params, n_states)


def _backward_messages(coupling: float, h: np.ndarray, length: int) -> np.ndarray:
    """``backward[i]``: log weight of everything from site ``i + 1`` onward, given the state at site ``i``.

    ``backward[-1]`` is empty and so zero. Shared by :func:`_simulate_open_chain`
    and :func:`open_chain_log_partition`, so the two agree by construction
    rather than by two copies of the same recursion.
    """
    n_states = h.shape[0]
    log_transfer = coupling * np.eye(n_states) + h[np.newaxis, :]
    backward = np.zeros((length, n_states))
    for i in range(length - 2, -1, -1):
        backward[i] = _logsumexp(log_transfer + backward[i + 1][np.newaxis, :], axis=1)
    return backward


def open_chain_log_partition(coupling: float, h: np.ndarray, length: int) -> float:
    """Exact ``log Z`` for an open 1-D chain, by the same backward recursion :func:`_simulate_open_chain` samples from.

    A NumPy computation independent of ``phylo.opt.potts.log_partition``'s
    torch transfer matrix, so the two agreeing is a real cross-check (root
    ``CLAUDE.md``, "Pin to Independent Sources") rather than one
    implementation checked against itself.

    Parameters
    ----------
    coupling : float
        Scalar ``J``.
    h : np.ndarray
        External field, shape ``(n_states,)``.
    length : int
        Chain length, >= 1.

    Returns
    -------
    float
        ``log Z``.
    """
    backward = _backward_messages(coupling, h, length)
    return float(_logsumexp((h + backward[0])[np.newaxis, :], axis=1)[0])


def _simulate_open_chain(
    graph: PottsGraph, h: np.ndarray, seed: int, n_chains: int, n_states: int
) -> np.ndarray:
    """Exact backward-message sampler for an open 1-D chain.

    Moved from ``phylo.opt.potts.simulate_chains`` unchanged: the chain's
    backward messages give the conditional distributions directly, so the
    fixture carries no equilibration assumption (root ``CLAUDE.md``,
    "Simulate Component-Wise").
    """
    length = graph.n_nodes
    coupling = float(graph.coupling[0]) if graph.edges else 0.0
    rng = np.random.default_rng(seed)
    log_transfer = coupling * np.eye(n_states) + h[np.newaxis, :]
    backward = _backward_messages(coupling, h, length)

    chains = np.empty((n_chains, length), dtype=np.int64)
    first = _softmax(h + backward[0])
    chains[:, 0] = rng.choice(n_states, size=n_chains, p=first)
    for i in range(1, length):
        conditional = _softmax(log_transfer + backward[i][np.newaxis, :], axis=1)
        chains[:, i] = sample_rows(rng, conditional, chains[:, i - 1])
    return chains


def _simulate_by_gibbs(
    graph: PottsGraph,
    h: np.ndarray,
    seed: int,
    params: PottsLatticeParams,
    n_states: int,
) -> np.ndarray:
    """Single-site Gibbs/heat-bath MCMC on an arbitrary graph.

    No exact sampler exists in general (unlike the open chain), so this is
    the fallback the general ``PottsGraph`` representation requires. Every
    chain is updated in lockstep, vectorized over chains at each node.
    """
    rng = np.random.default_rng(seed)
    adjacency = _adjacency(graph)
    states = rng.integers(0, n_states, size=(params.n_chains, graph.n_nodes))

    for _ in range(params.burn_in):
        _gibbs_sweep(rng, states, adjacency, h, n_states)

    records = np.empty((params.sweeps, params.n_chains, graph.n_nodes), dtype=np.int64)
    for record in range(params.sweeps):
        for _ in range(params.thin):
            _gibbs_sweep(rng, states, adjacency, h, n_states)
        records[record] = states

    # Chain-major: chain 0's `sweeps` samples first, matching the docstring.
    return records.transpose(1, 0, 2).reshape(
        params.n_chains * params.sweeps, graph.n_nodes
    )


def _adjacency(graph: PottsGraph) -> list[list[tuple[int, float]]]:
    """Undirected adjacency list, ``(neighbor, J_ij)`` per node."""
    adjacency: list[list[tuple[int, float]]] = [[] for _ in range(graph.n_nodes)]
    for (i, j), coupling in zip(graph.edges, graph.coupling, strict=True):
        adjacency[i].append((j, float(coupling)))
        adjacency[j].append((i, float(coupling)))
    return adjacency


def _gibbs_sweep(
    rng: np.random.Generator,
    states: np.ndarray,
    adjacency: list[list[tuple[int, float]]],
    h: np.ndarray,
    n_states: int,
) -> None:
    """One heat-bath update of every node, in a random order, in place.

    ``states`` has shape ``(n_chains, n_nodes)``; every chain is updated at
    the same node simultaneously, one categorical draw per chain via
    :func:`~phylo.numerics.sample_rows`.
    """
    n_chains = states.shape[0]
    categories = np.arange(n_states)
    chain_index = np.arange(n_chains)
    for node in rng.permutation(len(adjacency)):
        local = np.tile(h, (n_chains, 1))
        for neighbor, coupling in adjacency[node]:
            local = local + coupling * (
                states[:, neighbor][:, np.newaxis] == categories[np.newaxis, :]
            )
        probs = _softmax(local, axis=1)
        states[:, node] = sample_rows(rng, probs, chain_index)


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
