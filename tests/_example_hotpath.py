"""Example scaffolding for the regression + benchmark harness.

This module is NOT production code. It exists purely so the harness
(``tests/regression/`` and ``tests/benchmarks/``) has a small, concrete
"hot function" to exercise, pending real numerical kernels being added
to this repository.

The prefixed underscore keeps pytest from collecting this file as a test
module itself (it contains no ``test_*`` functions), while still allowing
it to be imported directly by the regression and benchmark tests.
"""

from __future__ import annotations

import numpy as np


def pairwise_distance(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Compute pairwise Euclidean distances between two 2D point sets.

    Parameters
    ----------
    x : np.ndarray
        Array of shape (n, d) -- n points in d dimensions.
    y : np.ndarray
        Array of shape (m, d) -- m points in d dimensions.

    Returns
    -------
    np.ndarray
        Array of shape (n, m) where entry [i, j] is the Euclidean
        distance between x[i] and y[j].

    Notes
    -----
    Fully vectorized via NumPy broadcasting (no explicit Python loops
    over points), per the project's convention of preferring
    array-based implementations on hot paths.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    # (n, 1, d) - (1, m, d) -> (n, m, d) via broadcasting, then reduce
    # over the last (coordinate) axis.
    diff = x[:, np.newaxis, :] - y[np.newaxis, :, :]
    return np.sqrt(np.sum(diff * diff, axis=-1))
