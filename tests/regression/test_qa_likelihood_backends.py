"""Regression test for phylo.qa.likelihood_backends.

The figure's claim is that the backends agree -- with brute-force
marginalization on a small tree, and with the NumPy reference at scale. This
pins the numbers the script computes before handing them to matplotlib
(qa/CLAUDE.md), including the distinction the figure exists to make: an
absolute deviation grows with the site count, a relative one does not.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from phylo.qa.likelihood_backends import (
    BACKEND_TOLERANCE,
    FLOAT64_EPS,
    BackendAgreement,
    agreement_against_brute_force,
    agreement_against_numpy,
    build_figure,
    main,
)

from tests._fixtures import (
    EIGHT_TAXA,
    FIXTURES_DIR,
    FOUR_TAXA,
    SMALL_SITES,
    load_fixture,
)


def test_every_backend_matches_brute_force_at_machine_precision() -> None:
    # The independent-oracle claim: an exhaustive sum over internal states,
    # a different algorithm from the pruning recursion it checks.
    agreement = agreement_against_brute_force(load_fixture(FOUR_TAXA))

    assert set(agreement.deviations) == {"NumPy", "PyTorch", "Rust"}
    for backend, deviation in agreement.deviations.items():
        assert deviation <= BACKEND_TOLERANCE, backend


def test_accelerated_backends_match_numpy_relatively_at_scale() -> None:
    # At 200k sites the absolute deviation is far above the small-size
    # tolerance while the relative one sits at the float64 floor. That
    # contrast is the figure's point, so it is pinned rather than assumed.
    agreement = agreement_against_numpy(load_fixture(FOUR_TAXA))

    for backend, relative in agreement.relative.items():
        assert relative < 1e-10, backend
    assert agreement.n_sites == 200_000


def test_relative_and_absolute_deviations_are_consistent() -> None:
    agreement = agreement_against_numpy(load_fixture(SMALL_SITES))

    for backend, absolute in agreement.deviations.items():
        expected = absolute / abs(agreement.reference)
        assert agreement.relative[backend] == pytest.approx(expected)


def test_reference_log_likelihood_is_negative_and_scales_with_sites() -> None:
    # A log-likelihood is a sum of log probabilities, so it is negative and
    # grows in magnitude with the site count -- the reason an absolute
    # tolerance fixed at one size does not transfer to another.
    small = agreement_against_numpy(load_fixture(SMALL_SITES))
    large = agreement_against_numpy(load_fixture(FOUR_TAXA))

    assert small.reference < 0.0
    assert abs(large.reference) > abs(small.reference)


def test_eight_taxon_fixture_scores_without_brute_force() -> None:
    agreement = agreement_against_numpy(load_fixture(EIGHT_TAXA))

    assert agreement.n_taxa == 8
    assert set(agreement.relative) == {"PyTorch", "Rust"}


def _synthetic(label: str, relative: float) -> BackendAgreement:
    return BackendAgreement(
        label=label,
        n_taxa=4,
        n_sites=100,
        reference=-250.0,
        deviations={"PyTorch": relative * 250.0, "Rust": relative * 250.0},
        relative={"PyTorch": relative, "Rust": relative},
    )


def test_caption_states_both_scales_and_is_plain_text() -> None:
    brute = BackendAgreement(
        label="4 taxa",
        n_taxa=4,
        n_sites=400,
        reference=-500.0,
        deviations={"NumPy": 1e-12, "PyTorch": 1e-12, "Rust": 5e-13},
        relative={"NumPy": 2e-15, "PyTorch": 2e-15, "Rust": 1e-15},
    )
    fig, caption = build_figure(brute, [_synthetic("a", 1e-13)])
    try:
        # main.tex reads the caption verbatim, so LaTeX specials break the
        # document build (qa/CLAUDE.md).
        assert not set(caption) & set("_%\\&#")
        # Both numbers must appear: the figure exists to contrast them.
        assert "relative" in caption
        assert "absolute" in caption
        assert f"{BACKEND_TOLERANCE:.0e}" in caption
    finally:
        fig.clf()


def test_float64_eps_is_the_documented_constant() -> None:
    assert float(np.finfo(np.float64).eps) == FLOAT64_EPS


def test_main_writes_a_figure_and_its_caption(tmp_path: Path) -> None:
    written = main(
        [
            "--params",
            str(FIXTURES_DIR / SMALL_SITES),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert written.figure_path.is_file()
    assert written.caption_path.read_text() == written.caption
