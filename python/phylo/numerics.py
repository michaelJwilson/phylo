"""Numerical helpers with no model knowledge, importable from anywhere.

Everything here is arithmetic. It names no model, no alignment and no tree, so
`phylo.opt` and `phylo.learn` may import it without acquiring an application
reference, and `phylo.sim` may import it without inverting the layering.

The module exists because the alternative failed. Vectorized categorical
sampling was written three times -- in `phylo.sim.simulate`, `phylo.opt.potts`
and `phylo.opt.hmm` -- and the three copies drifted: two of them omitted the
guard the third had, which is the difference between a valid state index and
one past the end of the alphabet. A helper with one home cannot drift from
itself.
"""

from __future__ import annotations

import numpy as np


def sample_rows(
    rng: np.random.Generator, distributions: np.ndarray, rows: np.ndarray
) -> np.ndarray:
    """Draw one categorical index per entry of ``rows``, from the row it selects.

    Inverse-CDF sampling, vectorized over the whole batch: one uniform draw
    per entry, placed against the cumulative probabilities of the row that
    entry names.

    **The last cumulative column is clamped to 1.** A probability row that
    sums to ``1 - 4e-16`` after rounding leaves a sliver of the unit interval
    above its own total, and a draw landing there is past every column --
    which the obvious formulations report as an index one past the end of the
    alphabet. The clamp sends that draw to the last category, which is where
    it belongs. This is not hypothetical arithmetic: the drift is ordinary
    ``float64`` behaviour for a normalized row, and the draw is reachable
    because ``rng.random`` returns values in ``[0, 1)``.

    Parameters
    ----------
    rng : np.random.Generator
        Seeded generator. One value is drawn per entry of ``rows``, in order,
        so a caller's stream consumption does not depend on the outcome.
    distributions : np.ndarray
        Row-stochastic, shape ``(n_rows, n_categories)``. Rows need only sum
        to 1 within rounding.
    rows : np.ndarray
        Which row each draw comes from, shape ``(n_draws,)``, entries in
        ``[0, n_rows)``.

    Returns
    -------
    np.ndarray
        Sampled category per entry, shape ``(n_draws,)``, entries in
        ``[0, n_categories)``.

    Raises
    ------
    ValueError
        If ``distributions`` is not 2-D. A 1-D distribution has no row to
        select, and passing one is a mistake worth naming rather than
        broadcasting past.
    """
    if distributions.ndim != 2:
        msg = (
            f"expected distributions of shape (n_rows, n_categories), got "
            f"{distributions.shape}"
        )
        raise ValueError(msg)

    cumulative = np.cumsum(distributions, axis=1)
    cumulative[:, -1] = 1.0
    draws = rng.random(size=(int(rows.shape[0]),))
    selected: np.ndarray = np.argmax(draws[:, np.newaxis] < cumulative[rows], axis=1)
    return selected
