"""QA figure: a worked simulation example -- Newick string and alignment.

Renders the Newick string and a compact table of simulated aligned
sequences for a small-taxa ``simulation_params.yaml``-format fixture, so the
technical document shows an actual generated example rather than a
schematic. Per ``sim/CLAUDE.md``'s "k-state, e.g. 4" convention, states are
shown nucleotide-coded (A/C/G/T) for ``k == 4``.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.axes import Axes
from matplotlib.transforms import Bbox

from phylo.qa.figure import QAFigure, write_qa_figure
from phylo.sim.params import SimulationParams, load_simulation_params
from phylo.sim.simulate import SimulatedDataset, simulate_alignment
from phylo.sim.tree import preorder

_MODEL_NAME = "Jukes-Cantor"
_NUCLEOTIDES = "ACGT"


def state_label(state: int, k: int) -> str:
    """Render a simulated state as a nucleotide letter when ``k == 4``.

    Parameters
    ----------
    state : int
        Simulated state, in ``[0, k)``.
    k : int
        Number of states in the model.

    Returns
    -------
    str
        The nucleotide letter for ``state`` when ``k == 4``; otherwise the
        state's decimal digit, since the nucleotide labelling only applies
        to the 4-state alphabet.
    """
    if k == len(_NUCLEOTIDES):
        return _NUCLEOTIDES[state]
    return str(state)


def render_sim_example(dataset: SimulatedDataset, n_sites_shown: int, ax: Axes) -> int:
    """Draw ``dataset``'s Newick string and a sliced alignment table on ``ax``.

    Parameters
    ----------
    dataset : SimulatedDataset
        The simulated alignment to display.
    n_sites_shown : int
        Number of leading alignment columns to tabulate.
    ax : matplotlib.axes.Axes
        Axes to draw into.

    Returns
    -------
    int
        The number of sites actually shown (``min(n_sites_shown,
        dataset.n_sites)``), for callers that need it (e.g. the caption).
    """
    n_shown = min(n_sites_shown, dataset.n_sites)
    leaves = sorted(dataset.alignment)
    rows = [
        [
            state_label(int(state), dataset.k)
            for state in dataset.alignment[name][:n_shown]
        ]
        for name in leaves
    ]

    ax.axis("off")
    ax.text(
        0.0,
        1.0,
        dataset.newick,
        transform=ax.transAxes,
        fontsize=7,
        family="monospace",
        va="top",
        wrap=True,
    )
    table = ax.table(
        cellText=rows,
        rowLabels=leaves,
        colLabels=[str(i) for i in range(n_shown)],
        cellLoc="center",
        bbox=Bbox.from_bounds(0.0, 0.0, 1.0, 0.6),
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    return n_shown


def build_caption(params: SimulationParams, n_sites_shown: int) -> str:
    """Caption text for the worked-example figure.

    Parameters
    ----------
    params : SimulationParams
        The parameters the figure was rendered from.
    n_sites_shown : int
        Number of leading alignment columns tabulated.

    Returns
    -------
    str
        Plain-text caption, safe to ``\\input`` into LaTeX verbatim.
    """
    n_taxa = sum(1 for node in preorder(params.tau) if node.is_leaf)
    n_shown = min(n_sites_shown, params.n_sites)
    return (
        f"Worked example: {n_taxa}-taxon alignment simulated under the "
        f"{_MODEL_NAME} model (seed {params.seed}, {params.n_sites} sites "
        f"total), showing the generated Newick topology and the first "
        f"{n_shown} of {params.n_sites} simulated sites."
    )


def render_sim_example_figure(
    params_path: Path, output_dir: Path, n_sites_shown: int = 10
) -> QAFigure:
    """Render the worked-example QA figure and caption from a params yaml.

    Parameters
    ----------
    params_path : Path
        Path to a ``simulation_params.yaml``-format file.
    output_dir : Path
        Directory the figure and caption are written into.
    n_sites_shown : int
        Number of leading alignment columns to tabulate.

    Returns
    -------
    QAFigure
        Paths to the written figure and caption, and the caption text.
    """
    params = load_simulation_params(params_path)
    dataset = simulate_alignment(
        tau=params.tau,
        k=params.k,
        pi=params.pi,
        seed=params.seed,
        n_sites=params.n_sites,
    )
    fig, ax = plt.subplots(figsize=(6, 4))
    n_shown = render_sim_example(dataset, n_sites_shown, ax)
    caption = build_caption(params, n_shown)
    qa_figure = write_qa_figure(output_dir, "sim_example", fig, caption)
    plt.close(fig)
    return qa_figure


def main() -> None:
    """CLI entry point: ``python -m phylo.qa.sim_example --params ... --output-dir ...``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--params", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--n-sites-shown", type=int, default=10)
    args = parser.parse_args()
    qa_figure = render_sim_example_figure(
        args.params, args.output_dir, args.n_sites_shown
    )
    print(f"Wrote {qa_figure.figure_path} and {qa_figure.caption_path}")


if __name__ == "__main__":
    main()
