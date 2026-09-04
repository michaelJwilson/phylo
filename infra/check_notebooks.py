"""Re-execute the committed notebooks and compare what they print.

`docs/nb/` ships notebooks with their outputs committed, and until now
nothing re-ran them. That gap was not theoretical: `phylo.sim.hmm` landing in
#182 broke `hmm.ipynb`'s import outright, and #187 switched three call sites
to a Rust sampler that could have moved every simulated number. Both were
caught by hand. A `docs/tex/` figure cannot rot that way because CI
regenerates it and byte-compares the rebuilt PDF; this is the notebooks'
equivalent (issue #203).

**Text is compared; images are not.** Every number a notebook prints is
deterministic given its seeds, so a re-executed stream output must match the
committed one exactly. Rendered figures embed metadata that is not stable
across matplotlib builds, and comparing them would reproduce the
`SOURCE_DATE_EPOCH` problem `docs/CLAUDE.md` records for `docs/tex/` -- for a
weaker payoff, since the printed numbers are what the notebooks assert with.
What is checked for a figure is that the cell still produced one.

Exits 0 when every notebook agrees, 1 on the first that does not, printing a
unified diff of the cell's output.
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path
from typing import Any

import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = REPO_ROOT / "docs" / "nb"

# Generous: `potts_chain.ipynb` trains eight policies. A timeout here would
# read as a rotted notebook, which is the one failure this must not invent.
CELL_TIMEOUT = 900


def text_outputs(cell: dict[str, Any]) -> list[str]:
    """Everything a code cell printed, in order.

    Streams and text/plain execute results count; images do not, for the
    reason the module docstring gives.

    Parameters
    ----------
    cell : dict[str, Any]
        A notebook cell.

    Returns
    -------
    list[str]
        One entry per text-bearing output.
    """
    collected = []
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream":
            collected.append("".join(output.get("text", [])))
            continue
        if output.get("output_type") not in {"execute_result", "display_data"}:
            continue
        data = output.get("data", {})
        if "image/png" in data:
            # A figure's `text/plain` is `<Figure size 560x340 with 1 Axes>`
            # -- a repr of the artist, not a measurement, and it moves with
            # the figure size. The figure itself is counted by `image_count`.
            continue
        plain = data.get("text/plain")
        if plain is not None:
            collected.append("".join(plain) if isinstance(plain, list) else str(plain))
    return collected


def image_count(cell: dict[str, Any]) -> int:
    """How many outputs of this cell carry an image."""
    return sum(
        1 for output in cell.get("outputs", []) if "image/png" in output.get("data", {})
    )


def compare(path: Path) -> list[str]:
    """Re-execute ``path`` and report where it disagrees with what is committed.

    Parameters
    ----------
    path : Path
        The notebook to check.

    Returns
    -------
    list[str]
        Human-readable differences; empty when the notebook still produces
        what it claims.
    """
    committed = nbformat.read(path, as_version=4)
    executed = nbformat.read(path, as_version=4)
    # The notebooks resolve the repository root by walking up from the
    # working directory, so they are executed where they live.
    try:
        NotebookClient(
            executed,
            timeout=CELL_TIMEOUT,
            resources={"metadata": {"path": str(path.parent)}},
        ).execute()
    except CellExecutionError as failure:
        # A notebook that no longer runs is the loudest way it can rot, and
        # reporting that as a crash of this tool rather than as a failure of
        # that notebook would bury it. `phylo.sim.hmm` landing in #182 broke
        # `hmm.ipynb`'s import outright, which is exactly this case.
        return [f"{path.name} did not execute:\n{failure}"]

    problems = []
    code_cells = [
        (before, after)
        for before, after in zip(committed.cells, executed.cells, strict=True)
        if before.cell_type == "code"
    ]
    for index, (before, after) in enumerate(code_cells, start=1):
        expected, realized = text_outputs(before), text_outputs(after)
        if expected != realized:
            diff = difflib.unified_diff(
                "".join(expected).splitlines(keepends=True),
                "".join(realized).splitlines(keepends=True),
                fromfile=f"{path.name} cell {index}: committed",
                tofile=f"{path.name} cell {index}: re-executed",
            )
            problems.append("".join(diff))
        if image_count(before) != image_count(after):
            problems.append(
                f"{path.name} cell {index}: committed {image_count(before)} "
                f"figure(s), re-executed produced {image_count(after)}"
            )
    return problems


def main(argv: list[str] | None = None) -> int:
    """Check every notebook, or the ones named.

    Returns
    -------
    int
        0 when all agree, 1 otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "notebooks",
        nargs="*",
        type=Path,
        help="Notebooks to check; default is every one under docs/nb/.",
    )
    arguments = parser.parse_args(argv)
    paths = arguments.notebooks or sorted(NOTEBOOK_DIR.glob("*.ipynb"))
    if not paths:
        print(f"no notebooks found under {NOTEBOOK_DIR}", file=sys.stderr)
        return 1

    failed = False
    for path in paths:
        problems = compare(path)
        if problems:
            failed = True
            print(f"FAIL {path}", file=sys.stderr)
            for problem in problems:
                print(problem, file=sys.stderr)
        else:
            print(f"ok   {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
