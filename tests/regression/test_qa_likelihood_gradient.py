"""Regression test for phylo.qa.likelihood_gradient.

The figure's claim is that autograd through the PyTorch pruning recursion
agrees with central finite differences of the independent NumPy likelihood.
This pins that agreement, the scale-free way of measuring it, and the
U-shaped step-size behaviour panel (b) reports -- the numbers the script
computes before matplotlib sees them (qa/CLAUDE.md).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from phylo.qa.likelihood_gradient import (
    FD_STEP,
    RELATIVE_TOLERANCE,
    TEST_ABSOLUTE_TOLERANCE,
    _relative_disagreement,
    build_figure,
    gradients,
    main,
    step_sweep,
)

from tests._fixtures import FIXTURES_DIR, FOUR_TAXA, load_fixture


def test_autograd_matches_finite_differences() -> None:
    # Two implementations (PyTorch and NumPy) and two methods (analytic and
    # numerical), so agreement is evidence rather than self-consistency.
    _, autograd, finite = gradients(load_fixture(FOUR_TAXA))

    assert _relative_disagreement(autograd, finite) < 1e-5


def test_one_gradient_per_branch_in_branch_order() -> None:
    names, autograd, finite = gradients(load_fixture(FOUR_TAXA))

    assert len(names) == len(autograd) == len(finite) == 5
    assert len(set(names)) == len(names)


def test_gradients_are_non_trivial() -> None:
    # A zero gradient everywhere would satisfy any agreement check while
    # proving nothing, which is the coverage-theatre failure mode.
    _, autograd, _ = gradients(load_fixture(FOUR_TAXA))

    assert np.all(np.abs(autograd) > 1.0)


def test_relative_disagreement_is_scale_free() -> None:
    # The property the figure depends on: scaling both gradients by the same
    # factor -- as increasing the site count does -- leaves the relative
    # disagreement unchanged, while the absolute one grows with it.
    autograd = np.array([2.0, -4.0])
    finite = np.array([2.0002, -4.0004])

    base = _relative_disagreement(autograd, finite)
    scaled = _relative_disagreement(autograd * 1000.0, finite * 1000.0)

    assert scaled == pytest.approx(base)
    assert base == pytest.approx(1e-4)


def test_relative_disagreement_is_zero_for_identical_gradients() -> None:
    values = np.array([1.5, -2.5, 3.0])
    assert _relative_disagreement(values, values) == 0.0


def test_caption_records_both_the_relative_and_absolute_readings() -> None:
    names = ["a", "b"]
    autograd = np.array([10.0, -20.0])
    finite = np.array([10.001, -20.002])
    fig, caption = build_figure(
        names, autograd, finite, [1e-4, 1e-6, 1e-8], [1e-5, 1e-7, 1e-4]
    )
    try:
        assert not set(caption) & set("_%\\&#")
        assert "relative" in caption
        assert "absolute" in caption
        assert f"{TEST_ABSOLUTE_TOLERANCE:.0e}" in caption
        # The step must be stated: a finite-difference check is only
        # meaningful near the minimum of the U.
        assert f"{FD_STEP:.0e}" in caption
    finally:
        fig.clf()


def test_relative_tolerance_constant_is_documented() -> None:
    assert 0.0 < RELATIVE_TOLERANCE < 1.0


@pytest.mark.release
def test_step_sweep_is_u_shaped() -> None:
    # Panel (b)'s claim: truncation error falls as the step shrinks while
    # cancellation grows, so the best step is interior, not at either end.
    # Release-gated -- it re-scores the alignment twice per branch per step.
    steps, worst = step_sweep(load_fixture(FOUR_TAXA))

    best = int(np.argmin(worst))
    assert 0 < best < len(steps) - 1
    assert worst[0] > worst[best]
    assert worst[-1] > worst[best]


def test_main_writes_a_figure_and_its_caption(tmp_path: Path) -> None:
    written = main(
        [
            "--params",
            str(FIXTURES_DIR / FOUR_TAXA),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert written.figure_path.is_file()
    assert written.caption_path.read_text() == written.caption
