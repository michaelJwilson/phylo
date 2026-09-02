"""Regression test for phylo.qa.figure.write_qa_figure.

Pins that the PDF it writes does not embed Type 3 fonts: GitHub's blob
viewer fails to render them ("Error rendering embedded code"), which is
what motivated scoping ``pdf.fonttype``/``ps.fonttype`` to 42 in
``write_qa_figure`` (see issue #76) rather than just checking the figure
renders without raising (CLAUDE.md's no-coverage-theatre rule).
"""

from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from phylo.qa.figure import write_qa_figure

mpl.use("Agg")


def test_write_qa_figure_does_not_embed_type3_fonts(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    ax.set_title("regression fixture")

    qa_figure = write_qa_figure(tmp_path, "stem", fig, "caption text")

    pdf_bytes = qa_figure.figure_path.read_bytes()
    assert b"/Subtype/Type3" not in pdf_bytes
    assert b"/Subtype /Type3" not in pdf_bytes


def test_write_qa_figure_does_not_mutate_global_font_rc(tmp_path: Path) -> None:
    fig, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])

    before = (mpl.rcParams["pdf.fonttype"], mpl.rcParams["ps.fonttype"])
    write_qa_figure(tmp_path, "stem", fig, "caption text")
    after = (mpl.rcParams["pdf.fonttype"], mpl.rcParams["ps.fonttype"])

    assert before == after
