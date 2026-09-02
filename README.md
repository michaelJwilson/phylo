# phylo

[![CI](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An agent-assisted exploration of modern optimization for phylogenetic
inference — a high-performance Python package with a Rust-accelerated backend
(`phylo.oxiphylo`, via [PyO3](https://pyo3.rs)/[maturin](https://www.maturin.rs)).

Two separable things live here, and keeping them separable is a constraint
rather than an observation. **The infrastructure** — the build, the checks,
the release process, the agentic workflow — mentions no phylogenetics and
would transplant to an unrelated scientific project unchanged. **The
application** is the science. This file is ordered accordingly:
infrastructure first, application last.

## Quick start

```
uv sync --locked --all-extras
source .venv/bin/activate
pytest -m "not release"
```

`pytest -m "not release"` is what CI runs and what you want while developing.
Plain `pytest` additionally runs the release-gated tests — one extra test for
roughly seven times the wall clock, because the exhaustive topological checks
grow combinatorially in taxon count. [DEV.md](DEV.md) has the measured
numbers.

[INSTALL.md](INSTALL.md) covers the full workflow: prerequisites, building the
Rust extension, running both test suites, the checks CI enforces, dependency
audits, and building the docs.

---

# Infrastructure

## Development is agent-assisted, and the workflow is the point

Work reaches this repository through a loop designed so that an agent's
output is reviewable on the same terms as a human's — the interesting claim
being not that an agent wrote the code, but that the repository can tell
whether the code is right.

1. **A ticket is filed** through [`.github/ISSUE_TEMPLATE/task.yml`](.github/ISSUE_TEMPLATE/task.yml),
   which asks for the outcome, the non-goals, and — the field that does the
   work — *how it will be validated*. Blank issues are disabled: a task that
   cannot say what would falsify it does not get filed.
2. **A plan is posted to the thread** and the issue is labelled `planned`.
   The plan is reviewed before any code exists, which is the cheapest point
   to reject an approach.
3. **A maintainer applies `approved`.** Only then may a pull request open,
   and it must implement the plan already in the thread; a plan that turns
   out to be flawed gets a revised plan posted, not a silent correction.
4. **The pull request answers [a fixed checklist](.github/pull_request_template.md)** —
   the Definition of Done, benchmark numbers, the realized value of any
   tolerance-based test beside the tolerance it was checked against, and
   which documents the change made untrue.
5. **A release is itself a ticket**, gating on `infra/release.sh` passing
   before a version is tagged.

`CLAUDE.md` is the contract an agent reads first, and it is authoritative:
where it and any other document disagree, it wins. Each module carries its
own `CLAUDE.md` for the rules local to it. Labels are defined in
[`.github/labels.yml`](.github/labels.yml) and applied by a workflow, so the
taxonomy cannot drift from the documentation; [`infra/TICKETING.md`](infra/TICKETING.md)
describes the board.

None of the above is specific to phylogenetics, and that is deliberate.

## What enforces the claims

Eight required checks run on every pull request: `ruff` and `mypy --strict`,
`clippy` and `cargo fmt`, the Rust and Python suites, the Sphinx build with
warnings as errors, the technical-document build, and dependency audits.
Beyond the usual, three rules shape what the suite is allowed to contain:

- **No coverage theatre.** A test asserting only shapes, or only that
  nothing raised, is forbidden. Gaps are left unwritten and tracked as
  issues.
- **Every accelerated path keeps its reference implementation.** The
  vectorized NumPy version stays as the oracle the Rust, PyTorch and future
  GPU backends are pinned against — deleting the slow path removes the only
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
| `docs/source/` | Sphinx API documentation, built from the docstrings |

---

# Application

## Mixed discrete and continuous optimization

The scientific problem is a search over phylogenetic tree topologies — the
large parsimony problem — scoring each candidate by its likelihood under a
model of character substitution.

Its structure is what makes it interesting, and what makes the machinery
reusable: the search is **discrete** over topologies, but scoring any one
topology requires a **continuous** fit of that tree's branch lengths, rate
matrix and root distribution. Neither half is separable from the other. A
better topology scored with badly fitted parameters looks worse than a poor
one scored well.

That shape is not unique to phylogenies. Felsenstein pruning, the HMM forward
algorithm, and the Potts transfer matrix are the same sum-product recursion
on different graphs — a tree, a chain, a lattice — so the same discrete/
continuous interface applies to all three, and the project treats that as a
design constraint rather than a coincidence.

The techniques brought to bear are modern ones: automatic differentiation for
the continuous fit, a reinforcement-learned proposal policy in place of
hand-designed topological moves, and — further out — attention over a
canonical serialization of the tree itself.

## What exists

Simulation under a `k`-state Jukes–Cantor model with the truth retained
alongside the data; Felsenstein pruning in vectorized NumPy, in differentiable
PyTorch, and in Rust, each pinned against brute-force marginalization; NNI and
SPR neighbourhood generators validated against closed-form neighbour counts.
[ROADMAP.md](ROADMAP.md) records what has landed against each milestone and
what has not.

## Reading the science

| Document | Contents |
| --- | --- |
| [ROADMAP.md](ROADMAP.md) | The scientific goal, the requirements, and milestone status |
| `docs/tex/` | The technical document: background, equations, algorithms |
| [`docs/draft.pdf`](docs/draft.pdf) | The rendered document, committed and regenerated by `infra/build_technical_doc.sh` |
| [`docs/tex/figures/`](docs/tex/figures) | The QA figures the document rests on, committed so a changed plot is visible in review |

Every figure in the document is rendered from the code it reports on and
ships with a caption naming the seed, the sizes, and the model that produced
it. A figure that cannot say what generated it is not evidence.

## License

MIT — see [LICENSE](LICENSE).
