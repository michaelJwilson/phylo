# qa/

High-level oversight scripts: the plots and tables that give scientific
figures for `docs/tex/` and validate the application frameworks (`sim/` now,
`likelihood/`, `opt/`, `search/` later) beyond what a unit test checks.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

One script per figure or table, each taking a `simulation_params.yaml`-format
input and producing a rendered figure plus a caption that states the seed,
sizes, and model used to generate it. `figure.py` holds the shared
figure/caption-writing helper every script uses, so output is named and
formatted consistently rather than per script.

`infra/build_technical_doc.sh` runs these scripts and feeds their output into
the LaTeX build; this package does not itself invoke `latexmk` or know where
`docs/tex/` figures ultimately land beyond the output directory it is given.

## Local rules

- **Render what the application already computed, never recompute it.**
  A QA script calls into `sim`/`likelihood`/`opt`/`search` for topology,
  probabilities, or trajectories; it does not reimplement the science it is
  reporting on.
- **A figure ships with its caption, and the caption ships with its
  generating parameters.** Seed, sizes, and model name are read from the same
  `simulation_params.yaml`-format input the figure was rendered from, per
  `sim/CLAUDE.md`'s ground-truth-retention rule — never hand-written
  separately from what actually ran.
- **A caption file is plain text, not LaTeX.** `docs/tex/main.tex` pulls it in
  verbatim via `\input`, so it must not contain unescaped LaTeX special
  characters (`_`, `%`, `\`, `&`, `#`).
- **Regression-test the layout, not the rendering.** matplotlib output isn't
  numerically pinnable; the coordinates and text a script computes before
  handing them to matplotlib are, and that is what a test pins.
