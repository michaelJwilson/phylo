"""Example hot function shared by the regression and benchmark tests.

Scaffolding, not production code: it gives the test harness something concrete
to exercise until real numerical kernels land.
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
    Vectorized via NumPy broadcasting, with no Python-level loop over points.
    """
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    # (n, 1, d) - (1, m, d) -> (n, m, d) via broadcasting, then reduce
    # over the last (coordinate) axis.
    diff = x[:, np.newaxis, :] - y[np.newaxis, :, :]
    return np.sqrt(np.sum(diff * diff, axis=-1))
