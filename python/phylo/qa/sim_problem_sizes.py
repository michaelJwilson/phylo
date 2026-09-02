"""QA table: problem-size parameters across the simulation fixtures.

Tabulates taxa count, site count, seed, and Monte Carlo tolerance for a set
of ``simulation_params.yaml``-format fixtures, read directly from the yaml
rather than hardcoded, so the technical document's numbers cannot drift from
what the regression suite actually runs (``tests/regression/test_jc_simulate.py``).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from phylo.qa.figure import QATable, latex_integer, write_qa_table
from phylo.sim.params import SimulationParams, load_simulation_params
from phylo.sim.tree import preorder


def _n_taxa(params: SimulationParams) -> int:
    return sum(1 for node in preorder(params.tau) if node.is_leaf)


def _escape(text: str) -> str:
    """Escape the LaTeX specials a fixture filename can contain."""
    return text.replace("_", "\\_")


def render_problem_sizes(
    fixture_names: list[str], params_by_fixture: dict[str, SimulationParams]
) -> str:
    """Build a LaTeX ``tabular`` of problem-size parameters, one row per fixture.

    A typeset table rather than a matplotlib image: it matches the
    surrounding type, scales with the document, and can be selected and
    searched. The numbers are read from the yaml, so they cannot drift from
    what the regression suite runs.

    Parameters
    ----------
    fixture_names : list[str]
        Fixture filenames, in the row order to display.
    params_by_fixture : dict[str, SimulationParams]
        Loaded parameters, keyed by the same filenames.

    Returns
    -------
    str
        A complete ``tabular`` environment.
    """
    rows = [
        " & ".join(
            [
                f"\\texttt{{{_escape(fixture_name)}}}",
                str(_n_taxa(params_by_fixture[fixture_name])),
                latex_integer(params_by_fixture[fixture_name].n_sites),
                # A seed is an identifier, not a magnitude: separators would
                # make 20260902 look like a quantity rather than a date.
                str(params_by_fixture[fixture_name].seed),
                f"{params_by_fixture[fixture_name].tolerance:g}",
            ]
        )
        + r" \\"
        for fixture_name in fixture_names
    ]
    return "\n".join(
        [
            r"\begin{tabular}{lrrrr}",
            r"  \toprule",
            r"  Fixture & Taxa & Sites & Seed & Tolerance \\",
            r"  \midrule",
            *(f"  {row}" for row in rows),
            r"  \bottomrule",
            r"\end{tabular}",
        ]
    )


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


def render_problem_sizes_table(fixture_paths: list[Path], output_dir: Path) -> QATable:
    """Render the problem-sizes QA table and caption from a set of params yamls.

    Parameters
    ----------
    fixture_paths : list[Path]
        Paths to ``simulation_params.yaml``-format files, in the row order
        to display.
    output_dir : Path
        Directory the table fragment and caption are written into.

    Returns
    -------
    QATable
        Paths to the written table and caption, and the caption text.
    """
    fixture_names = [path.name for path in fixture_paths]
    params_by_fixture = {
        path.name: load_simulation_params(path) for path in fixture_paths
    }
    body = render_problem_sizes(fixture_names, params_by_fixture)
    caption = build_caption(fixture_names)
    return write_qa_table(output_dir, "sim_problem_sizes", body, caption)


def main() -> None:
    """CLI entry point: ``python -m phylo.qa.sim_problem_sizes --params ... --params ... --output-dir ...``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--params", type=Path, required=True, action="append", dest="params"
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    qa_table = render_problem_sizes_table(args.params, args.output_dir)
    print(f"Wrote {qa_table.table_path} and {qa_table.caption_path}")


if __name__ == "__main__":
    main()
