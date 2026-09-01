"""Property-based tests for the example hot function.

See tests/_example_hotpath.py -- this is example scaffolding for the
property-testing pattern, not a test of production numerical code (none
exists in this repo yet). Complements, rather than replaces, the fixed-input
regression test in tests/regression/: hypothesis searches for edge cases
that violate a stated invariant, instead of pinning one specific input.
"""

from __future__ import annotations

import numpy as np
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.extra.numpy import arrays

from tests._example_hotpath import pairwise_distance

_finite = st.floats(
    min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False
)


def _point_set(max_points: int = 6):
    return st.integers(min_value=1, max_value=max_points).flatmap(
        lambda n: arrays(dtype=np.float64, shape=(n, 2), elements=_finite)
    )


@settings(max_examples=50)
@given(x=_point_set(), y=_point_set())
def test_pairwise_distance_is_nonnegative(x: np.ndarray, y: np.ndarray) -> None:
    assert np.all(pairwise_distance(x, y) >= 0.0)


@settings(max_examples=50)
@given(x=_point_set(), y=_point_set())
def test_pairwise_distance_is_transpose_symmetric(x: np.ndarray, y: np.ndarray) -> None:
    np.testing.assert_allclose(
        pairwise_distance(x, y), pairwise_distance(y, x).T, rtol=1e-8, atol=1e-8
    )


@settings(max_examples=50)
@given(x=_point_set())
def test_pairwise_distance_self_diagonal_is_zero(x: np.ndarray) -> None:
    result = pairwise_distance(x, x)
    np.testing.assert_allclose(np.diag(result), 0.0, atol=1e-8)
