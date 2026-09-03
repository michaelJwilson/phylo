# docs/

The technical document (`tex/`) and the API documentation (`source/`). Both
are generated artifacts whose output is committed, and that is what these
rules are about: a committed artifact that CI regenerates has to come out the
same everywhere, which constrains what the document may say.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

`tex/main.tex` is the document, `tex/references.bib` its bibliography, and
`tex/figures/` the figures, tables and captions `phylo.qa` generates — a
table ships as a `tabular` fragment the document `\input`s, not as an image,
so it matches the surrounding type. `draft.pdf` is the rendered result.
`source/` is Sphinx, built from the docstrings.

`infra/build_technical_doc.sh` regenerates every figure and then runs
`latexmk`. There is no partial rebuild, and nothing here invokes `latexmk`
itself.

**Committed:** `tex/main.tex`, `tex/references.bib`, `tex/figures/*.pdf`,
`tex/figures/*.tex`, `tex/figures/*_caption.txt`, `draft.pdf`,
`source/conf.py`, `source/index.rst`. Everything else under `docs/` is
`latexmk` output and gitignored.

## The reader

A well-educated developer with a scientific and performance-computing
background, but not an application expert — not a phylogeneticist. That sets
the formatting contract. Keep the body streamlined: hyperlinks and citations
over inline derivation. Push required application background — NNI, and other
standard algorithms — into the appendix and cite it from the point of use
rather than re-deriving it there. Treat the main text as a high-level view of
the current best-known approach in terms of the roadmap, not an exhaustive
record; link out to supporting documents for the studies that informed it.

## Local rules

- **Regenerate a figure; never edit one.** A figure, a table fragment and a
  caption are outputs of the script that produced them. Editing any by hand
  breaks the guarantee the whole arrangement exists for: that what the
  document shows cannot drift from what was measured.

- **The document reads captions and never restates them.** `\qacaptionread`
  pulls the file `phylo.qa` wrote, verbatim. So a body paragraph that
  describes a figure is restating a string it does not own, and the two will
  diverge. The caption says what a figure shows; the body says why it is
  there (issue #125, which cut 314 words of restatement from one section).

- **Every number must survive a rebuild on another machine.** CI rebuilds
  `draft.pdf`, rasterizes it, and byte-compares. A generated caption may
  therefore report only quantities *continuous* in their inputs. Issue #137
  is the instance: a caption quoted a Spearman rank correlation over an
  optimizer's output, and a rank statistic is discontinuous — perturbing the
  scores by one part in `1e12` moved it by 0.04. The build broke, but the
  deeper problem was that a number that unstable was not a measurement.
  Before quoting a computed value, perturb its inputs and check the caption
  is unchanged.

- **Machine-dependent numbers stay out of the document.** `DEV.md` forbids
  ranking performance on CI hardware, so a timing belongs in a benchmark. A
  caption gives the structural reason instead — "a full optimization against
  a single pruning pass", not "247 ms against 0.7 ms".

- **A LaTeX setting that looks global is global.** Scope one to the macro
  that needs it. Issue #118: `\endlinechar=-1` outside a group deleted the
  space at *every* source line break, so wrapped text set as
  "substitutionmodel" throughout. It survived review because the source was
  correct and only the output was wrong.

- **`latexmk` exits 0 on a broken reference**, so CI greps the log instead —
  for `multiply defined` as well as undefined. Both halves are load-bearing:
  the duplicate-label check was added after issue #104 introduced a second
  `eq:gtr` that a grep for "undefined" sailed past.

- **`source/index.rst` claims to cover every submodule**, so a new module
  gets an entry in the same PR. It was missing fourteen when issue #135
  repaired it, eight of them long-standing — which is how a stated invariant
  fails when nothing checks it.

- **`SOURCE_DATE_EPOCH` is pinned** in the build script, because matplotlib
  and `pdftex` both embed it as a creation date. Without it every rebuild
  differs and the staleness check is meaningless.

## Boundaries

These rules cover how the document is built and kept true, not what it says;
the science is the application modules' business.

`qa/CLAUDE.md` owns the writer's side of the caption contract — plain text,
no unescaped LaTeX specials, enforced by `figure.check_latex_safe`. The split
is at the file boundary: `qa/` writes captions, `docs/` reads them.
