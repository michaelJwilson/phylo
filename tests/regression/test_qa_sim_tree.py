"""Regression test for phylo.qa.sim_tree.

Pins the layout's numeric coordinates against branch lengths recomputed
independently, and the caption's content against the generating parameters
-- not just that the figure renders without raising (CLAUDE.md's
no-coverage-theatre rule).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from phylo.qa.sim_tree import build_caption, main, render_sim_tree_figure, tree_layout
from phylo.sim.params import load_simulation_params
from phylo.sim.tree import Node, preorder

FIXTURES = Path(__file__).parent / "fixtures"


def _expected_depth(node: Node, parent_depth: float, target: str) -> float | None:
    depth = parent_depth + (node.branch_length or 0.0)
    if node.name == target:
        return depth
    for child in node.children:
        found = _expected_depth(child, depth, target)
        if found is not None:
            return found
    return None


def test_tree_layout_depths_match_branch_length_sums() -> None:
    params = load_simulation_params(FIXTURES / "simulation_params_8taxa.yaml")
    layout = tree_layout(params.tau)

    for node in preorder(params.tau):
        expected = _expected_depth(params.tau, 0.0, node.name)
        assert expected is not None
        depth, _y = layout[node.name]
        assert depth == expected


def test_tree_layout_gives_every_leaf_a_distinct_ordered_y() -> None:
    params = load_simulation_params(FIXTURES / "simulation_params_8taxa.yaml")
    layout = tree_layout(params.tau)
    leaves = [node.name for node in preorder(params.tau) if node.is_leaf]

    leaf_ys = [layout[name][1] for name in leaves]
    assert leaf_ys == list(range(len(leaves)))


def test_render_sim_tree_figure_writes_caption_with_generating_truth(
    tmp_path: Path,
) -> None:
    params_path = FIXTURES / "simulation_params_8taxa.yaml"
    params = load_simulation_params(params_path)

    qa_figure = render_sim_tree_figure(params_path, tmp_path)

    assert qa_figure.figure_path.is_file()
    assert qa_figure.figure_path.stat().st_size > 0
    assert qa_figure.caption == build_caption(params)
    assert str(params.seed) in qa_figure.caption
    assert "8 taxa" in qa_figure.caption
    assert "Jukes-Cantor" in qa_figure.caption


def test_main_cli_writes_the_same_figure_as_the_library_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    params_path = FIXTURES / "simulation_params_8taxa.yaml"
    monkeypatch.setattr(
        "sys.argv",
        ["sim_tree", "--params", str(params_path), "--output-dir", str(tmp_path)],
    )

    main()

    figure_path = tmp_path / "sim_tree.pdf"
    caption_path = tmp_path / "sim_tree_caption.txt"
    assert figure_path.is_file()
    assert caption_path.read_text() == build_caption(
        load_simulation_params(params_path)
    )
    captured = capsys.readouterr()
    assert str(figure_path) in captured.out
    assert str(caption_path) in captured.out
