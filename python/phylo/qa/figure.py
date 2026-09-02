"""Shared QA figure/caption writing, so every QA script formats consistently.

A figure without the parameters that generated it recorded alongside it is
not QA-usable (see ``sim/CLAUDE.md``'s ground-truth-retention rule); this
module is where that convention is enforced once, rather than per script.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib as mpl
from matplotlib.figure import Figure


@dataclass(frozen=True)
class QAFigure:
    """A rendered QA figure together with its caption.

    Parameters
    ----------
    figure_path : Path
        Path the figure was written to.
    caption_path : Path
        Path the caption text was written to.
    caption : str
        The caption text itself.
    """

    figure_path: Path
    caption_path: Path
    caption: str


def write_qa_figure(output_dir: Path, stem: str, fig: Figure, caption: str) -> QAFigure:
    """Write ``fig`` and ``caption`` under ``output_dir``, named from ``stem``.

    Parameters
    ----------
    output_dir : Path
        Directory to write into; created if missing.
    stem : str
        Base filename, without extension, shared by both outputs.
    fig : matplotlib.figure.Figure
        Figure to save as a PDF (vector, for inclusion in the LaTeX build).
    caption : str
        Caption text to write alongside the figure, plain text -- callers
        must not pass unescaped LaTeX special characters (see this
        directory's ``CLAUDE.md``).

    Returns
    -------
    QAFigure
        Paths written to, and the caption text.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    figure_path = output_dir / f"{stem}.pdf"
    caption_path = output_dir / f"{stem}_caption.txt"
    # matplotlib's PDF backend defaults to embedding text as Type 3 fonts
    # (pdf.fonttype=3), which GitHub's pdf.js-based blob viewer fails to
    # render ("Error rendering embedded code"). Type 42 embeds TrueType
    # outlines instead, which pdf.js renders correctly; scoped to this call
    # so it doesn't change matplotlib's global rc state for callers.
    with mpl.rc_context({"pdf.fonttype": 42, "ps.fonttype": 42}):
        fig.savefig(figure_path)
    caption_path.write_text(caption)
    return QAFigure(figure_path=figure_path, caption_path=caption_path, caption=caption)
