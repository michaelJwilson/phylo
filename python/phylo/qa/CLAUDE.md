# qa/

High-level oversight scripts: the plots and tables that give scientific
figures for `docs/tex/`, and that validate `sim/`, `likelihood/`, `opt/`,
`search/` and `learn/` beyond what a unit test checks.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

One script per figure or table, each taking a declarative parameters file and
producing a rendered figure plus a caption that states the seed, sizes, and
model used to generate it. The format is that model's own — the
phylogenetic figures take `simulation_params.yaml`, the optimization figures
take the Potts and HMM fixtures `phylo.opt` defines — because the
ground-truth-retention rule is about the caption matching what actually ran,
not about one file layout. `figure.py` holds the shared
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
  characters (`_`, `%`, `\`, `&`, `#`). The single exception is `\_`, which
  `figure.latex_integer` uses as a thousands separator. This is enforced by
  `figure.check_latex_safe`, called from every writer, rather than asserted
  once per caption test: a contract every caller must satisfy belongs in the
  function every caller goes through.
- **A table is typeset, not drawn.** `figure.write_qa_table` emits a LaTeX
  `tabular` fragment for `main.tex` to `\input`. A matplotlib table saved as
  an image does not match the surrounding type, does not scale with the
  document, and cannot be selected or searched.
- **Regression-test the layout, not the rendering.** matplotlib output isn't
  numerically pinnable; the coordinates and text a script computes before
  handing them to matplotlib are, and that is what a test pins.
