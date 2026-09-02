"""QA table: problem-size parameters across the simulation fixtures.

Tabulates taxa count, site count, seed, and Monte Carlo tolerance for a set
of ``simulation_params.yaml``-format fixtures, read directly from the yaml
rather than hardcoded, so the technical document's numbers cannot drift from
what the regression suite actually runs (``tests/regression/test_jc_simulate.py``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

from phylo.qa.figure import QAFigure, write_qa_figure
from phylo.sim.params import SimulationParams, load_simulation_params
from phylo.sim.tree import preorder


def _n_taxa(params: SimulationParams) -> int:
    return sum(1 for node in preorder(params.tau) if node.is_leaf)


def render_problem_sizes(
    fixture_names: list[str], params_by_fixture: dict[str, SimulationParams], ax: Axes
) -> None:
    """Draw a table of problem-size parameters, one row per fixture, on ``ax``.

    Parameters
    ----------
    fixture_names : list[str]
        Fixture filenames, in the row order to display.
    params_by_fixture : dict[str, SimulationParams]
        Loaded parameters, keyed by the same filenames.
    ax : matplotlib.axes.Axes
        Axes to draw into.
    """
    rows = [
        [
            fixture_name,
            str(_n_taxa(params_by_fixture[fixture_name])),
            str(params_by_fixture[fixture_name].n_sites),
            str(params_by_fixture[fixture_name].seed),
            str(params_by_fixture[fixture_name].tolerance),
        ]
        for fixture_name in fixture_names
    ]

    ax.axis("off")
    table = ax.table(
        cellText=rows,
        colLabels=["Fixture", "Taxa", "Sites", "Seed", "Tolerance"],
        cellLoc="center",
        loc="center",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.auto_set_column_width(col=list(range(5)))


def build_caption(fixture_names: list[str]) -> str:
    """Caption text for the problem-sizes table.

    Parameters
    ----------
    fixture_names : list[str]
        Fixture filenames tabulated, in row order.

    Returns
    -------
    str
        Plain-text caption, safe to ``\\input`` into LaTeX verbatim.
    """
    return (
        f"Problem-size parameters across the {len(fixture_names)} simulation "
        "regression fixtures backing the Jukes-Cantor simulation test: taxa "
        "count, site count, seed, and the Monte Carlo tolerance each "
        "validates simulated substitution frequencies within."
    )


def render_problem_sizes_figure(
    fixture_paths: list[Path], output_dir: Path
) -> QAFigure:
    """Render the problem-sizes QA table and caption from a set of params yamls.

    Parameters
    ----------
    fixture_paths : list[Path]
        Paths to ``simulation_params.yaml``-format files, in the row order
        to display.
    output_dir : Path
        Directory the figure and caption are written into.

    Returns
    -------
    QAFigure
        Paths to the written figure and caption, and the caption text.
    """
    fixture_names = [path.name for path in fixture_paths]
    params_by_fixture = {
        path.name: load_simulation_params(path) for path in fixture_paths
    }
    fig, ax = plt.subplots(figsize=(6, 1.5 + 0.4 * len(fixture_paths)))
    render_problem_sizes(fixture_names, params_by_fixture, ax)
    caption = build_caption(fixture_names)
    qa_figure = write_qa_figure(output_dir, "sim_problem_sizes", fig, caption)
    plt.close(fig)
    return qa_figure


def main() -> None:
    """CLI entry point: ``python -m phylo.qa.sim_problem_sizes --params ... --params ... --output-dir ...``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--params", type=Path, required=True, action="append", dest="params"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    qa_figure = render_problem_sizes_figure(args.params, args.output_dir)
    print(f"Wrote {qa_figure.figure_path} and {qa_figure.caption_path}")


if __name__ == "__main__":
    main()
