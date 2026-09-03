"""Regression tests for the Potts-lattice/graph simulator (issue #170).

Two independent oracles, per root `CLAUDE.md` ("Pin to Independent
Sources"):

* The general (Gibbs) sampler is validated at two exhaustively enumerable
  sizes -- 3-state 3x3 open (19,683 configurations) and 2-state 4x4 periodic
  (65,536) -- against single- and pair-site marginals computed by full
  enumeration, a computation sharing no code with the sampler under test,
  within a stated Monte Carlo tolerance (standard error over independent
  chains, the same pattern `tests/regression/sim/test_jc_simulate.py` uses
  for the alignment simulator).
* The 1-D chain dispatch is validated separately, by exact reduction to
  `phylo.opt.potts.log_partition`'s transfer-matrix `log Z` at the same
  `rtol` `tests/regression/opt/test_opt_potts.py` pins -- a reduction to an
  exact result, not sampler-vs-sampler agreement.

See `tests/regression/sim/test_potts_validation.py` for the loader's
guardrails.
"""

from __future__ import annotations

from itertools import product

import numpy as np
import pytest
import torch
from numpy.testing import assert_allclose
from phylo.opt.potts import log_partition as opt_log_partition
from phylo.sim.graph import BoundaryCondition, PottsGraph, lattice_graph
from phylo.sim.potts import (
    PottsLatticeParams,
    load_potts_lattice_params,
    open_chain_log_partition,
    simulate_potts,
)

from tests._fixtures import FIXTURES_DIR

FIXTURE = FIXTURES_DIR / "potts_lattice_params.yaml"

# Matches tests/regression/opt/test_opt_potts.py's _RTOL_ORACLE: both
# transfer-matrix computations are exact, so machine precision is the bar.
_RTOL_ORACLE = 1e-12


@pytest.mark.parametrize("length", [1, 2, 3, 5, 8])
def test_open_chain_log_partition_matches_the_transfer_matrix_oracle(
    length: int,
) -> None:
    coupling, field = 0.75, np.array([0.40, -0.10, -0.30])
    expected = float(
        opt_log_partition(
            torch.tensor(coupling, dtype=torch.float64),
            torch.as_tensor(field, dtype=torch.float64),
            length,
        )
    )
    actual = open_chain_log_partition(coupling, field, length)
    assert_allclose(actual, expected, rtol=_RTOL_ORACLE)


def _brute_force_single_and_pair_marginals(
    graph: PottsGraph, field: np.ndarray, n_states: int
) -> tuple[np.ndarray, np.ndarray]:
    """Exact single-site marginals and the pair-site marginal of ``graph.edges[0]``.

    Full enumeration over every one of ``n_states ** graph.n_nodes``
    configurations, sharing no code with ``simulate_potts``.
    """
    configs = np.array(list(product(range(n_states), repeat=graph.n_nodes)))
    edge_i = np.array([i for i, _ in graph.edges])
    edge_j = np.array([j for _, j in graph.edges])
    agreement = (configs[:, edge_i] == configs[:, edge_j]).astype(np.float64)
    energy = agreement @ graph.coupling + field[configs].sum(axis=1)
    weights = np.exp(energy - energy.max())
    probs = weights / weights.sum()

    single = np.stack(
        [
            np.bincount(configs[:, node], weights=probs, minlength=n_states)
            for node in range(graph.n_nodes)
        ]
    )

    i0, j0 = graph.edges[0]
    joint_index = configs[:, i0] * n_states + configs[:, j0]
    pair = np.bincount(
        joint_index, weights=probs, minlength=n_states * n_states
    ).reshape(n_states, n_states)

    return single, pair


def _mc_tolerance(expected: np.ndarray, n_chains: int, multiplier: float) -> np.ndarray:
    """``multiplier`` standard errors of a Monte Carlo frequency over ``n_chains`` independent chains."""
    variance = np.clip(expected * (1.0 - expected), 0.0, None)
    return multiplier * np.sqrt(variance / n_chains)


# (shape, boundary, n_states, coupling, field, n_chains, burn_in). Full
# enumeration (19,683 and 65,536 configurations, vectorized) is under 0.1 s
# each; the Gibbs sampling that dominates the wall clock is sized to keep
# both cases under ~2 s combined -- no @pytest.mark.release gate needed
# (DEV.md's CI budget) -- while `n_chains` still keeps the 5-standard-error
# margin below comfortably tight (<= 0.06 at the worst-case p = 0.5 cell).
_ENUMERATION_CASES = [
    pytest.param(
        (3, 3),
        BoundaryCondition.OPEN,
        3,
        0.5,
        [0.40, -0.10, -0.30],
        2000,
        150,
        id="3state_3x3_open_19683_configs",
    ),
    pytest.param(
        (4, 4),
        BoundaryCondition.PERIODIC,
        2,
        0.4,
        [0.30, -0.30],
        2000,
        200,
        id="2state_4x4_periodic_65536_configs",
    ),
]


@pytest.mark.parametrize(
    ("shape", "boundary", "n_states", "coupling", "field", "n_chains", "burn_in"),
    _ENUMERATION_CASES,
)
def test_simulated_marginals_match_exact_enumeration(
    shape: tuple[int, ...],
    boundary: BoundaryCondition,
    n_states: int,
    coupling: float,
    field: list[float],
    n_chains: int,
    burn_in: int,
) -> None:
    graph = lattice_graph(shape, boundary, coupling)
    raw_field = np.asarray(field, dtype=np.float64)
    h = raw_field - float(
        np.log(np.exp(raw_field).sum())
    )  # gauge-fix, as the loader does
    expected_single, expected_pair = _brute_force_single_and_pair_marginals(
        graph, h, n_states
    )

    params = PottsLatticeParams(
        n_states=n_states,
        shape=shape,
        boundary=boundary,
        coupling=coupling,
        field=h,
        n_chains=n_chains,
        burn_in=burn_in,
        sweeps=1,
        thin=1,
        seed=20260903,
    )
    chains = simulate_potts(graph, h, params.seed, params)
    assert chains.shape == (n_chains, graph.n_nodes)

    observed_single = np.stack(
        [
            np.bincount(chains[:, node], minlength=n_states) / n_chains
            for node in range(graph.n_nodes)
        ]
    )
    tolerance_single = _mc_tolerance(expected_single, n_chains, multiplier=5.0)
    deviation_single = np.abs(observed_single - expected_single)
    assert np.all(deviation_single <= tolerance_single), (
        f"max single-site deviation {deviation_single.max():.4f} exceeds "
        f"5 standard errors (max {tolerance_single.max():.4f})"
    )

    i0, j0 = graph.edges[0]
    observed_pair = np.zeros((n_states, n_states))
    for a in range(n_states):
        for b in range(n_states):
            observed_pair[a, b] = np.mean((chains[:, i0] == a) & (chains[:, j0] == b))
    tolerance_pair = _mc_tolerance(expected_pair, n_chains, multiplier=5.0)
    deviation_pair = np.abs(observed_pair - expected_pair)
    assert np.all(deviation_pair <= tolerance_pair), (
        f"max pair-site deviation {deviation_pair.max():.4f} exceeds "
        f"5 standard errors (max {tolerance_pair.max():.4f})"
    )


def test_general_path_shape_and_alphabet() -> None:
    params = load_potts_lattice_params(FIXTURE)
    graph = lattice_graph(params.shape, params.boundary, params.coupling)
    chains = simulate_potts(graph, params.field, params.seed, params)
    assert chains.shape == (params.n_chains * params.sweeps, graph.n_nodes)
    assert set(np.unique(chains)) <= set(range(params.n_states))


def test_simulation_is_reproducible_from_the_seed() -> None:
    params = load_potts_lattice_params(FIXTURE)
    graph = lattice_graph(params.shape, params.boundary, params.coupling)
    first = simulate_potts(graph, params.field, params.seed, params)
    second = simulate_potts(graph, params.field, params.seed, params)
    assert np.array_equal(first, second)


def test_the_loader_canonicalizes_the_field_gauge() -> None:
    params = load_potts_lattice_params(FIXTURE)
    assert_allclose(float(np.exp(params.field).sum()), 1.0, rtol=1e-14)


def test_coupling_raises_the_frequency_of_adjacent_agreement() -> None:
    # Same generative check as tests/regression/opt/test_opt_potts.py's
    # chain-only version, on a general lattice: positive coupling rewards
    # agreeing neighbours, so simulated chains must agree more often across
    # a bond than independent draws from the same field would -- computed in
    # closed form, not simulated, so this is an analytic comparison.
    params = load_potts_lattice_params(FIXTURE)
    graph = lattice_graph(params.shape, params.boundary, params.coupling)
    chains = simulate_potts(graph, params.field, params.seed, params)
    last_sweep = chains.reshape(params.n_chains, params.sweeps, graph.n_nodes)[:, -1, :]

    i0, j0 = graph.edges[0]
    observed = float((last_sweep[:, i0] == last_sweep[:, j0]).mean())
    independent = float((np.exp(params.field) ** 2).sum())
    assert observed > independent


def test_burn_in_sweeps_and_thin_are_ignored_on_the_exact_1d_path() -> None:
    # The exact backward-message sampler needs no equilibration (module
    # docstring), so the general MCMC knobs are inert on this path: two
    # PottsLatticeParams differing only in burn_in/sweeps/thin must produce
    # identical output at a fixed seed, and the output is always one row per
    # chain regardless of `sweeps`.
    graph = lattice_graph((5,), BoundaryCondition.OPEN, 0.5)
    field = np.array([0.30, -0.15, -0.15])
    lax = PottsLatticeParams(
        n_states=3,
        shape=(5,),
        boundary=BoundaryCondition.OPEN,
        coupling=0.5,
        field=field,
        n_chains=30,
        seed=3,
        burn_in=0,
        sweeps=1,
        thin=1,
    )
    strict = PottsLatticeParams(
        n_states=3,
        shape=(5,),
        boundary=BoundaryCondition.OPEN,
        coupling=0.5,
        field=field,
        n_chains=30,
        seed=3,
        burn_in=500,
        sweeps=9,
        thin=7,
    )

    lax_chains = simulate_potts(graph, field, 3, lax)
    strict_chains = simulate_potts(graph, field, 3, strict)
    assert lax_chains.shape == (30, 5)
    assert np.array_equal(lax_chains, strict_chains)
