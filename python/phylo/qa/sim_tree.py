"""QA figure: the assumed simulation tree, topology and branch lengths.

Renders the topology and branch lengths (expected substitutions/site) that
``phylo.sim.simulate`` draws an alignment over, from a
``simulation_params.yaml``-format file, as a labelled phylogram -- so the
tree a reader sees in the technical document is the one the simulator
actually used, not a schematic redrawn by hand.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from phylo.qa.figure import QAFigure, write_qa_figure
from phylo.sim.params import SimulationParams, load_simulation_params
from phylo.sim.tree import Node, edges, preorder

_MODEL_NAME = "Jukes-Cantor"


def tree_layout(tau: Node) -> dict[str, tuple[float, float]]:
    """Depth (x) and vertical order (y) for every node in ``tau``.

    Parameters
    ----------
    tau : Node
        Root of the topology to lay out.

    Returns
    -------
    dict[str, tuple[float, float]]
        Node name to ``(depth, y)``: ``depth`` is the sum of branch lengths
        from the root (expected substitutions/site); ``y`` is the node's
        vertical position, leaves evenly spaced in traversal order and
        internal nodes centred over their children.
    """
    depth: dict[str, float] = {}
    y: dict[str, float] = {}
    next_leaf_y = 0.0

    def _depth(node: Node, parent_depth: float) -> None:
        depth[node.name] = parent_depth + (node.branch_length or 0.0)
        for child in node.children:
            _depth(child, depth[node.name])

    def _y(node: Node) -> float:
        nonlocal next_leaf_y
        if node.is_leaf:
            y[node.name] = next_leaf_y
            next_leaf_y += 1.0
        else:
            child_ys = [_y(child) for child in node.children]
            y[node.name] = sum(child_ys) / len(child_ys)
        return y[node.name]

    _depth(tau, 0.0)
    _y(tau)
    return {name: (depth[name], y[name]) for name in depth}


def render_sim_tree(tau: Node, ax: Axes) -> dict[str, tuple[float, float]]:
    """Draw ``tau`` as a labelled phylogram on ``ax``.

    Parameters
    ----------
    tau : Node
        Root of the topology to draw.
    ax : matplotlib.axes.Axes
        Axes to draw into.

    Returns
    -------
    dict[str, tuple[float, float]]
        The layout from :func:`tree_layout`, for callers that need the
        plotted coordinates (e.g. a regression test).
    """
    layout = tree_layout(tau)
    for parent, child in edges(tau):
        parent_depth, parent_y = layout[parent.name]
        child_depth, child_y = layout[child.name]
        ax.plot(
            [parent_depth, parent_depth],
            [parent_y, child_y],
            color="black",
            linewidth=1,
        )
        ax.plot(
            [parent_depth, child_depth], [child_y, child_y], color="black", linewidth=1
        )
        midpoint = (parent_depth + child_depth) / 2
        assert child.branch_length is not None  # non-root, per Node's contract
        ax.text(
            midpoint,
            child_y,
            f"{child.branch_length:.2f}",
            fontsize=7,
            ha="center",
            va="bottom",
        )
    for node in preorder(tau):
        if node.is_leaf:
            node_depth, node_y = layout[node.name]
            ax.text(node_depth + 0.01, node_y, node.name, fontsize=9, va="center")

    ax.set_xlabel("Expected substitutions / site")
    ax.set_yticks([])
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
    return layout


def build_caption(params: SimulationParams) -> str:
    """Caption text for the simulation-tree figure.

    States the seed, taxa count, and evolutionary model, per
    ``sim/CLAUDE.md``'s ground-truth-retention rule -- a plot is only
    QA-usable alongside the parameters that generated it.

    Parameters
    ----------
    params : SimulationParams
        The parameters the figure was rendered from.

    Returns
    -------
    str
        Plain-text caption, safe to ``\\input`` into LaTeX verbatim.
    """
    n_taxa = sum(1 for node in preorder(params.tau) if node.is_leaf)
    return (
        f"Simulated topology for {n_taxa} taxa under the {_MODEL_NAME} model "
        f"(seed {params.seed}), branch lengths labelled in expected "
        "substitutions per site."
    )


def render_sim_tree_figure(params_path: Path, output_dir: Path) -> QAFigure:
    """Render the simulation-tree QA figure and caption from a params yaml.

    Parameters
    ----------
    params_path : Path
        Path to a ``simulation_params.yaml``-format file.
    output_dir : Path
        Directory the figure and caption are written into.

    Returns
    -------
    QAFigure
        Paths to the written figure and caption, and the caption text.
    """
    params = load_simulation_params(params_path)
    fig, ax = plt.subplots(figsize=(6, 4))
    render_sim_tree(params.tau, ax)
    caption = build_caption(params)
    qa_figure = write_qa_figure(output_dir, "sim_tree", fig, caption)
    plt.close(fig)
    return qa_figure


def main() -> None:
    """CLI entry point: ``python -m phylo.qa.sim_tree --params ... --output-dir ...``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--params", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    qa_figure = render_sim_tree_figure(args.params, args.output_dir)
    print(f"Wrote {qa_figure.figure_path} and {qa_figure.caption_path}")


if __name__ == "__main__":
    main()
