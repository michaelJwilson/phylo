# phylo

[![CI](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Agent-assisted development of mixed discrete/continuous optimization, applied
to phylogenetic inference. A Rust-accelerated backend (`phylo.oxiphylo`, via
[PyO3](https://pyo3.rs)/[maturin](https://www.maturin.rs)) and autodiff.

Two concerns stay separate. **The infrastructure** — the build, the checks,
the release process, the agentic workflow — names no application. **The
application** is the science.

## Quick start

```
uv sync --locked --all-extras
source .venv/bin/activate
pytest -m "not release"
```

[INSTALL.md](INSTALL.md) covers the full workflow: prerequisites, building the
Rust extension, running both test suites, the checks CI enforces, dependency
audits, and building the docs.

---

# Infrastructure

## Development is agent-assisted

An agent's output is reviewed on the same terms as a human's. The claim is not
that an agent wrote the code; it is that the process establishes whether the
code is right.

1. **A ticket is filed** through [`.github/ISSUE_TEMPLATE/task.yml`](.github/ISSUE_TEMPLATE/task.yml),
   which asks for the outcome, the non-goals, and — the field that does the
   work — *how it will be validated*. Blank issues are disabled: a task that
   cannot say what would falsify it does not get filed.
2. **A plan is posted to the thread** and the issue is labelled `planned`.
   Review happens before any code exists, the cheapest point to reject an
   approach.
3. **A maintainer applies `approved`.** Only then may a pull request open, and
   it must implement the plan already in the thread. A plan that turns out to
   be flawed gets a revised plan posted, not a silent correction.
4. **The pull request answers [a fixed checklist](.github/pull_request_template.md)**:
   the Definition of Done, benchmark numbers, the realized value of any
   tolerance-based test beside the tolerance it was checked against, and which
   documents the change made untrue.
5. **A release is itself a ticket**, gated on `infra/release.sh` passing before
   a version is tagged.

`CLAUDE.md` is the contract an agent reads first, and it is authoritative:
where it and any other document disagree, it wins. Each module carries its own
`CLAUDE.md` for the rules local to it. [`.github/labels.yml`](.github/labels.yml)
defines the labels and a workflow applies them, so the taxonomy cannot drift
from the documentation.

## What enforces the claims

Eight required checks run on every pull request: `ruff` and `mypy --strict`,
`clippy` and `cargo fmt`, the Rust and Python suites, the Sphinx build with
warnings as errors, the technical-document build, and dependency audits.
Three further rules constrain what the suite may contain:

- **No coverage theatre.** A test asserting only shapes, or only that nothing
  raised, is forbidden. Gaps are left unwritten and tracked as issues.
- **Every accelerated path keeps its reference implementation.** The
  vectorized NumPy version stays as the oracle the Rust, PyTorch and future
  GPU backends are pinned against. Deleting the slow path removes the only
  thing that says the fast path is right.
- **Correctness comes from an independent source**, not from a second
  backend: analytic results, brute-force computation, or exhaustive
  enumeration.

| Document | Contents |
| --- | --- |
| [INSTALL.md](INSTALL.md) | Installing, building, running the tests, working locally |
| [DEV.md](DEV.md) | Repository layout, test layout, CI jobs, the CI budget, the release procedure |
| [CHANGELOG.md](CHANGELOG.md) | What has landed, per dated release |
| `CLAUDE.md` | The authoritative conventions |
| `docs/CLAUDE.md` | How the technical document is built and kept true |
| `docs/source/` | Sphinx API documentation, built from the docstrings |

---

# Application

## Mixed discrete and continuous optimization

The scientific problem is a search over phylogenetic tree topologies — the
large parsimony problem — scoring each candidate by its likelihood under a
model of character substitution.

Its structure is what makes the machinery reusable: the search is **discrete**
over topologies, but scoring any one topology requires a **continuous** fit of
that tree's branch lengths, rate matrix and root distribution. Neither half
separates from the other. A better topology scored with badly fitted
parameters looks worse than a poor one scored well.

That shape is not unique to phylogenies. Felsenstein pruning, the HMM forward
algorithm, and the Potts transfer matrix are the same sum-product recursion on
different graphs — a tree, a chain, a lattice — so one discrete/continuous
interface serves all three. The project treats that as a design constraint
rather than a coincidence.

Automatic differentiation performs the continuous fit. A reinforcement-learned
proposal policy is intended to replace hand-designed topological moves; the
estimator and the phylogenetic environment exist, a trained agent does not.

## What exists

Simulation under a `k`-state Jukes–Cantor model, with the truth retained
alongside the data and validated against the closed-form transition
probabilities. Felsenstein pruning in vectorized NumPy, in differentiable
PyTorch, and in Rust, each pinned against brute-force marginalization to
machine precision. NNI and SPR neighbourhood generators, checked against
closed-form neighbour counts at `n = 5..8`. Hill climbing over topologies,
which reaches the exhaustively enumerated maximum from all 12 starting points
on a 6-taxon fixture. A gradient update costs 203 ms at `n = 100`, `L = 1000`.

[ROADMAP.md](ROADMAP.md) records what has landed against each milestone and
what has not.

## Reading the science

| Document | Contents |
| --- | --- |
| [ROADMAP.md](ROADMAP.md) | The scientific goal, the requirements, and milestone status |
| `docs/tex/` | The technical document: background, equations, algorithms |
| [`docs/draft.pdf`](docs/draft.pdf) | The rendered document, committed and regenerated by `infra/build_technical_doc.sh` |
| [`docs/tex/figures/`](docs/tex/figures) | The QA figures the document rests on, committed so a changed plot is visible in review |

Every figure in the document is rendered from the code it reports on and ships
with a caption naming the seed, the sizes, and the model that produced it. A
figure that cannot say what generated it is not evidence.

## License

MIT — see [LICENSE](LICENSE).
