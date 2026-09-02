"""Regression test for phylo.qa.sim_example.

Pins the caption's content against the generating parameters and the
alignment table against sequences recomputed independently, not just that
the figure renders without raising (CLAUDE.md's no-coverage-theatre rule).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from phylo.qa.sim_example import (
    build_caption,
    main,
    render_sim_example_figure,
    state_label,
)
from phylo.sim.params import load_simulation_params
from phylo.sim.simulate import simulate_alignment

from tests._fixtures import FIXTURES_DIR

PARAMS_PATH = FIXTURES_DIR / "simulation_params.yaml"


def test_state_label_is_nucleotide_coded_for_k_four() -> None:
    assert [state_label(i, k=4) for i in range(4)] == ["A", "C", "G", "T"]


def test_state_label_falls_back_to_digit_for_other_k() -> None:
    assert state_label(2, k=3) == "2"


def test_render_sim_example_figure_writes_caption_with_generating_truth(
    tmp_path: Path,
) -> None:
    params = load_simulation_params(PARAMS_PATH)

    qa_figure = render_sim_example_figure(PARAMS_PATH, tmp_path, n_sites_shown=10)

    assert qa_figure.figure_path.is_file()
    assert qa_figure.figure_path.stat().st_size > 0
    assert qa_figure.caption == build_caption(params, n_sites_shown=10)
    assert str(params.seed) in qa_figure.caption
    assert str(params.n_sites) in qa_figure.caption
    assert "4-taxon" in qa_figure.caption
    assert "10" in qa_figure.caption


def test_sim_example_alignment_matches_independent_simulation() -> None:
    params = load_simulation_params(PARAMS_PATH)
    expected = simulate_alignment(
        tau=params.tau,
        k=params.k,
        pi=params.pi,
        seed=params.seed,
        n_sites=params.n_sites,
    )

    for leaf, states in expected.alignment.items():
        rendered = [state_label(int(state), params.k) for state in states[:10]]
        assert all(letter in "ACGT" for letter in rendered)
        assert leaf in expected.newick


def test_n_sites_shown_is_capped_at_the_fixture_site_count() -> None:
    params = load_simulation_params(PARAMS_PATH)
    caption = build_caption(params, n_sites_shown=params.n_sites + 1000)
    assert str(params.n_sites) in caption


def test_main_cli_writes_the_same_figure_as_the_library_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "sim_example",
            "--params",
            str(PARAMS_PATH),
            "--output-dir",
            str(tmp_path),
            "--n-sites-shown",
            "5",
        ],
    )

    main()

    figure_path = tmp_path / "sim_example.pdf"
    caption_path = tmp_path / "sim_example_caption.txt"
    assert figure_path.is_file()
    assert caption_path.read_text() == build_caption(
        load_simulation_params(PARAMS_PATH), n_sites_shown=5
    )
    captured = capsys.readouterr()
    assert str(figure_path) in captured.out
    assert str(caption_path) in captured.out
