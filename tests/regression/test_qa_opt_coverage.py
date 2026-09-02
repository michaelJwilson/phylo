"""Regression test for phylo.qa.opt_coverage.

The figure's claim is that the intervals converge on their nominal rate as
the sample grows. Refitting at every size is what the technical-document
build is for, not what a per-PR test should pay for, so this pins the two
things that can be wrong cheaply: the counting, at one small size, and the
caption, which must report the numbers it was handed rather than numbers
somebody typed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from phylo.opt.hmm import load_hmm_params
from phylo.opt.potts import load_potts_params
from phylo.qa import opt_coverage
from phylo.qa.opt_coverage import (
    HMM_SIZES,
    NOMINAL,
    POTTS_SIZES,
    build_figure,
    hmm_coverage,
    potts_coverage,
)

from tests._fixtures import FIXTURES_DIR

POTTS_FIXTURE = FIXTURES_DIR / "potts_params.yaml"
HMM_FIXTURE = FIXTURES_DIR / "hmm_params.yaml"


def test_potts_coverage_counts_every_parameter_of_every_replicate() -> None:
    params = load_potts_params(POTTS_FIXTURE)
    covered, total = potts_coverage(params, n_chains=100, replicates=3)
    assert total == 3 * (1 + params.n_states)
    assert 0 <= covered <= total


def test_hmm_coverage_counts_every_parameter_of_every_replicate() -> None:
    params = load_hmm_params(HMM_FIXTURE)
    covered, total = hmm_coverage(params, n_sequences=150, replicates=2)
    per_replicate = (
        params.n_states + params.n_states**2 + params.n_states * params.n_symbols
    )
    assert total == 2 * per_replicate
    assert 0 <= covered <= total


def test_the_sizes_the_figure_sweeps_are_increasing() -> None:
    # The figure's whole argument is a trend, so a mis-ordered sweep would
    # make it unreadable rather than merely ugly.
    assert [size for size, _ in POTTS_SIZES] == sorted(size for size, _ in POTTS_SIZES)
    assert [size for size, _ in HMM_SIZES] == sorted(size for size, _ in HMM_SIZES)
    assert NOMINAL == 0.95


def test_the_caption_reports_the_numbers_it_was_given() -> None:
    potts = [(100, 158, 160), (400, 155, 160), (1600, 96, 100)]
    hmm = [(150, 168, 192), (600, 139, 144), (2400, 91, 96)]

    _, caption = build_figure(potts, hmm)

    assert "158/160 = 0.988 at 100" in caption
    assert "96/100 = 0.960 at 1600" in caption
    assert "168/192 = 0.875 at 150" in caption
    assert "91/96 = 0.948 at 2400" in caption
    # qa/CLAUDE.md: captions are plain text pulled into LaTeX verbatim.
    assert not set(caption) & set("_%\\&#")


def test_main_writes_a_figure_and_caption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The real sweep refits both models dozens of times and belongs to the
    # technical-document build, not to a per-PR test; the sizes are patched
    # down so the wiring is still exercised.
    monkeypatch.setattr(opt_coverage, "POTTS_SIZES", ((50, 2), (100, 2)))
    monkeypatch.setattr(opt_coverage, "HMM_SIZES", ((40, 1), (80, 1)))

    written = opt_coverage.main(
        [
            "--potts-params",
            str(POTTS_FIXTURE),
            "--hmm-params",
            str(HMM_FIXTURE),
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert written.figure_path.is_file()
    assert written.caption_path.read_text() == written.caption
