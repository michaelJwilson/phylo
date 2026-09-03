"""Benchmarks for `phylo.sim.potts.simulate_potts`.

See tests/regression/sim/test_potts.py for correctness. Two paths are
measured: the exact backward-message sampler on an open 1-D chain, and the
general single-site Gibbs/heat-bath sampler on a 2-D lattice -- the ratio
between them is what says how much of the general path's cost is the MCMC
sweep loop rather than the model itself.
"""

from __future__ import annotations

import math

import numpy as np
from phylo.sim.graph import BoundaryCondition, lattice_graph
from phylo.sim.potts import PottsLatticeParams, simulate_potts
from pytest_benchmark.fixture import BenchmarkFixture

_FIELD_3STATE = np.array([0.40, -0.10, -0.30])


def test_open_chain_potts_benchmark(benchmark: BenchmarkFixture) -> None:
    graph = lattice_graph((50,), BoundaryCondition.OPEN, coupling=0.6)
    params = PottsLatticeParams(
        n_states=3,
        shape=(50,),
        boundary=BoundaryCondition.OPEN,
        coupling=0.6,
        field=_FIELD_3STATE,
        n_chains=200,
        burn_in=0,
        sweeps=1,
        thin=1,
        seed=20260903,
    )

    result = benchmark(simulate_potts, graph, _FIELD_3STATE, params.seed, params)

    # Benchmarks assert shape/finiteness only -- correctness is pinned in
    # tests/regression/sim/test_potts.py.
    assert result.shape == (200, 50)
    assert math.isfinite(float(result.sum()))


def test_lattice_gibbs_potts_benchmark(benchmark: BenchmarkFixture) -> None:
    shape = (6, 6)
    graph = lattice_graph(shape, BoundaryCondition.OPEN, coupling=0.5)
    params = PottsLatticeParams(
        n_states=3,
        shape=shape,
        boundary=BoundaryCondition.OPEN,
        coupling=0.5,
        field=_FIELD_3STATE,
        n_chains=50,
        burn_in=50,
        sweeps=1,
        thin=1,
        seed=20260903,
    )

    result = benchmark(simulate_potts, graph, _FIELD_3STATE, params.seed, params)

    assert result.shape == (50, 36)
    assert math.isfinite(float(result.sum()))
