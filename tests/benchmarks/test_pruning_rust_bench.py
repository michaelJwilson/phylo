"""Benchmarks for the Rust CPU Felsenstein pruning backend.

See tests/regression/test_pruning_rust.py for correctness. Same (taxa, site)
fixtures as test_likelihood_pruning_bench.py and test_pruning_torch_bench.py
so the NumPy, PyTorch, and Rust numbers are directly comparable.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from pytest_benchmark.fixture import BenchmarkFixture
from snakes_and_ladders.likelihood import pruning, pruning_rust
from snakes_and_ladders.sim.params import load_simulation_params
from snakes_and_ladders.sim.simulate import simulate_alignment

from tests._fixtures import FIXTURES_DIR


@pytest.mark.parametrize(
    "fixture_name",
    [
        "simulation_params.yaml",  # 4 taxa, 200_000 sites
        "simulation_params_small_sites.yaml",  # 4 taxa, 20_000 sites
        "simulation_params_8taxa.yaml",  # 8 taxa, 200_000 sites
    ],
)
def test_rust_log_likelihood_benchmark(
    benchmark: BenchmarkFixture, fixture_name: str
) -> None:
    params = load_simulation_params(FIXTURES_DIR / fixture_name)
    dataset = simulate_alignment(
        tau=params.tau,
        k=params.k,
        pi=params.pi,
        rng=np.random.default_rng(params.seed),
        n_sites=params.n_sites,
    )

    result = benchmark(
        pruning_rust.log_likelihood, params.tau, params.k, params.pi, dataset.alignment
    )

    # Benchmarks only assert finiteness -- numerical correctness is pinned
    # separately in tests/regression/test_pruning_rust.py.
    assert math.isfinite(result)
    assert result < 0.0  # a log-likelihood, never positive


def test_numpy_vs_rust_forward_pass(benchmark: BenchmarkFixture) -> None:
    """Rust forward pass against the NumPy reference at a fixed size (report both)."""
    params = load_simulation_params(FIXTURES_DIR / "simulation_params_small_sites.yaml")
    dataset = simulate_alignment(
        tau=params.tau,
        k=params.k,
        pi=params.pi,
        rng=np.random.default_rng(params.seed),
        n_sites=params.n_sites,
    )

    numpy_result = pruning.log_likelihood(
        params.tau, params.k, params.pi, dataset.alignment
    )
    rust_result = benchmark(
        pruning_rust.log_likelihood, params.tau, params.k, params.pi, dataset.alignment
    )

    assert math.isclose(rust_result, numpy_result, abs_tol=1e-9)
