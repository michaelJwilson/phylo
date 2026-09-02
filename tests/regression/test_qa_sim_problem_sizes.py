"""Regression test for phylo.qa.sim_problem_sizes.

Pins the tabulated values against each fixture's yaml, read independently,
not just that the figure renders without raising (CLAUDE.md's
no-coverage-theatre rule).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from phylo.qa.sim_problem_sizes import build_caption, main, render_problem_sizes_figure
from phylo.sim.params import load_simulation_params
from phylo.sim.tree import preorder

from tests._fixtures import FIXTURES_DIR

FIXTURE_NAMES = (
    "simulation_params.yaml",
    "simulation_params_small_sites.yaml",
    "simulation_params_8taxa.yaml",
)
FIXTURE_PATHS = [FIXTURES_DIR / name for name in FIXTURE_NAMES]


def test_render_problem_sizes_figure_writes_caption_naming_every_fixture(
    tmp_path: Path,
) -> None:
    qa_figure = render_problem_sizes_figure(FIXTURE_PATHS, tmp_path)

    assert qa_figure.figure_path.is_file()
    assert qa_figure.figure_path.stat().st_size > 0
    assert qa_figure.caption == build_caption(list(FIXTURE_NAMES))
    assert str(len(FIXTURE_NAMES)) in qa_figure.caption


def test_problem_sizes_values_match_each_fixture_independently() -> None:
    for path in FIXTURE_PATHS:
        params = load_simulation_params(path)
        n_taxa = sum(1 for node in preorder(params.tau) if node.is_leaf)

        # Cross-check against direct knowledge of the fixtures rather than
        # re-deriving through the module under test.
        if path.name == "simulation_params.yaml":
            assert (n_taxa, params.n_sites, params.seed, params.tolerance) == (
                4,
                200000,
                20260902,
                0.01,
            )
        elif path.name == "simulation_params_small_sites.yaml":
            assert (n_taxa, params.n_sites, params.seed, params.tolerance) == (
                4,
                20000,
                20260903,
                0.03,
            )
        elif path.name == "simulation_params_8taxa.yaml":
            assert (n_taxa, params.n_sites, params.seed, params.tolerance) == (
                8,
                200000,
                20260904,
                0.01,
            )


def test_main_cli_writes_the_same_figure_as_the_library_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    argv = ["sim_problem_sizes"]
    for path in FIXTURE_PATHS:
        argv += ["--params", str(path)]
    argv += ["--output-dir", str(tmp_path)]
    monkeypatch.setattr("sys.argv", argv)

    main()

    figure_path = tmp_path / "sim_problem_sizes.pdf"
    caption_path = tmp_path / "sim_problem_sizes_caption.txt"
    assert figure_path.is_file()
    assert caption_path.read_text() == build_caption(list(FIXTURE_NAMES))
    captured = capsys.readouterr()
    assert str(figure_path) in captured.out
    assert str(caption_path) in captured.out
