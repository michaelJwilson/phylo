"""Benchmark for the example hot function.

See tests/_example_hotpath.py for what this exercises and why it's scaffolding.
"""

import numpy as np
from pytest_benchmark.fixture import BenchmarkFixture

from tests._example_hotpath import pairwise_distance


def test_pairwise_distance_benchmark(benchmark: BenchmarkFixture) -> None:
    np.random.seed(0)
    x = np.random.random((200, 3))
    y = np.random.random((150, 3))

    result = benchmark(pairwise_distance, x, y)

    # Benchmarks only assert shape -- numerical correctness is pinned
    # separately in tests/regression/test_pairwise_distance.py.
    assert result.shape == (200, 150)
