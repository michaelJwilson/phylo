# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Writing Style
1.  **(Reviewer) Time is money and context windows are finite and vital:** Be as concise as possible, use active voice, and lead with (only) the most important facts first.
2.  **Be precise:** Use exact facts and numbers ("40% faster") instead of vague intensifiers ("much faster").
3.  **Stay neutral and objective:** Avoid hype, subjective opinions, and weak qualifiers. Use nouns and verbs; avoid adjectives and adverbs.
4.  **Provide evidence:** Back every claim in PRs/commits with benchmark numbers, test validated outputs, or reproductions.
5.  **Maintain formatting:** Apply naming, terminology, and syntax consistently.

**Expected Reader:** a well-educated developer with scientific and performance-computing background, but not an application expert, e.g. phylogenetics. Keep tech. doc. streamlined — hyperlinks and citations over inline derivation — and push required application background (e.g. NNI, other standard algorithms) into a dedicated appendix, cited from the point of use rather than re-derived there. Treat the main text as a high-level overview of the current best-known approach (simulation, models, results) in terms of the roadmap, not an exhaustive record; link out to supporting docs, with plots, and results for dedicated studies that informed the technical doc. Adopt the style of an academic paper, supported by textbook style appendices on domain-specific material likely new to the developer.

## Project
`phylo` is a high-performance scientific repository. Correctness and reproducibility of numerical and scientific results take priority over convenience.

Two concerns are supported, and they must stay separable:

*   **Infrastructure:** the build, the checks, the release process, the agentic workflow. None of it names an application.
*   **Application:** phylogenetic substitution models, likelihoods, tree search, and the standards this science requires.

An infrastructure rule that acquires an application reference has lost the separation. Structure enforces it: `README.md` and `DEV.md` put infrastructure before application, and the file layout keeps them apart (`infra/` against `python/phylo/*` and `docs/tex/`).

## Repository Map
This file is authoritative. The remainder exist so there is not replication, and each has a defined task:

| Document | Job |
| --- | --- |
| `README.md` | What the project is, and where everything else lives |
| `INSTALL.md` | Installing, building, running the tests locally |
| `DEV.md` | Layout, the CI jobs, repository settings, the CI budget, how a change is reviewed |
| `ROADMAP.md` | The development loop, the scientific goal, requirements, and milestones |
| `STATUS.md` | What has landed against each roadmap milestone, the evidence, and the PR carrying it |
| `TICKETS.md` | The titles of the tickets that remain between `STATUS.md` and `ROADMAP.md` |
| `CHANGELOG.md` | What has landed, per dated release section; built from `changelog.d/` fragments by `towncrier` |
| `docs/tex/` | The technical document: background, equations, algorithms |

`python/phylo/sim/`, `likelihood/`, `opt/`, `learn/`, `search/`, `qa/`, `infra/`, and `docs/` each carry their own `CLAUDE.md`. Those add what applies only inside one module; they never override this file expect for the vital **writing style rules to be adopted at all times**. A rule that binds the whole repository belongs here, not in one of them.

## Environment & Tooling
*   **Python (3.12):** Manage via `uv`. Run `uv sync --locked --all-extras`. Regenerate locks with `uv lock` and commit `uv.lock` in the same PR.
*   **Rust:** Compiler pinned via `rust-toolchain.toml`. Lockfile is `Cargo.lock`. Update with `cargo update` and commit.
*   **Lint/Format (Python):** `ruff check .` and `ruff format --check .`
*   **Type Check (Python):** `mypy --strict`, over the paths in `pyproject.toml`'s `files` (`python/`, `tests/`).
*   **Lint/Format (Rust):** `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check`.
*   **Audit:** `pip-audit` (Python) and `cargo audit` (Rust).
*   **Docs:** Build with `sphinx-build -W` in `docs/source/`.

## Conventions
*   **Documentation Sync:** Any change affecting behavior, CI, dev setup, or math models must update, in the same PR, whichever of these it makes untrue: `README.md`, `CLAUDE.md` (including a module's), `DEV.md`, `INSTALL.md`, `ROADMAP.md`, `STATUS.md`, `TICKETS.md`, `docs/tex/`. If the change is user-visible, add a fragment under `changelog.d/` (see `changelog.d/README.md`) rather than editing `CHANGELOG.md` directly — `towncrier` merges fragments into `CHANGELOG.md` at release time, and CI's `towncrier check` enforces one exists.
*   **Single Version Source:** The package version lives exclusively in `Cargo.toml`'s `[package].version`.
*   **Package Surface:** `python/phylo/__init__.py` re-exports nothing beyond the package's own top-level utilities (currently `double`); import submodule contents explicitly (`from phylo.likelihood import ...`), not through the top-level namespace.
*   **Code Standards:** Use type hints on all Python functions. Do not introduce silent behavior changes (e.g., default parameters). Keep dependencies minimal and justify additions.

## Performance
*   **GPU (PyTorch, Triton, JAX):** Target if the hot path is data-parallel and earns $\ge 10\times$ speedup over vectorized NumPy at realistic problem sizes.
*   **Rust Backend (`oxiphylo`):** Target for CPU-bound hot paths (control flow, tree traversal, irregular memory access, small sizes).
*   **Autodiff:** **PyTorch**, decided. Its MPS backend is the path on Apple Silicon, which `ROADMAP.md` targets alongside CUDA.
*   **Measurement:** Benchmark candidates against the NumPy reference before committing to a port. Report both numbers in the PR.
*   **The Oracle:** Every accelerated kernel keeps its pure Python/NumPy implementation as an oracle. Regression tests must pin the accelerated output against it within an explicit tolerance.

## Testing & Quality Assurance
*   **Simulate Component-Wise:** Build fixtures by simulating from a known generative model under an explicitly seeded generator. Test components individually and in combination.
*   **Pin to Independent Sources:** Validate expected values against analytic results, brute-force computations, or secondary implementations with stated tolerances.
*   **Check Math Invariants:** Rows of a transition matrix sum to 1, a reversible model satisfies detailed balance, gradients match finite differences, and a fit's likelihood increases monotonically.
*   **Cross-Device Agreement Is a Tolerance:** `float32` and `float64` behave differently across CPU, CUDA, and Metal, and deep recursions accumulate that. Agreement is checked against the tolerance stated in `likelihood/CLAUDE.md`, with the measurements it is derived from, and implemented in `phylo.likelihood.device`, never bitwise. A discrepancy inside it is not a bug and must not be "fixed". Two rules that fall out of it: the tolerance is **relative**, because the log-likelihood is a sum over sites and an absolute bound fixed at one problem size does not transfer to another; and it is keyed on the **lowest precision** in the comparison, because Metal cannot do `float64` and one bound loose enough for `float32` would let a broken `float64` backend pass.
*   **No Coverage Theatre:** Tests asserting only output shapes or successful execution without exceptions are forbidden. Leave gaps unwritten and track them as GitHub issues rather than writing meaningless tests.
*   **Scientific Outputs:** The suite must emit plots and tables for the LaTeX technical document. Update the LaTeX captions concurrently. Every figure is rendered from the code it reports on, ships with a caption naming the seed, sizes and model that produced it, and is committed under `docs/tex/figures/` so a changed plot is visible in review rather than only after a document build.
*   **Time is money:** test and build frameworks should be justified, time/computationally, e.g. cahced; a high priority is to standup a minimal implementation against the ROADMAP.md with corresponding ablation studies with a fast test-driven development cycle.  Rely on the tests run on a PR as final validation where appropriate (late in development), rather than duplicating the effort - you will monitor the PR and fix issues before merging.

## Technical Document & Reference Sources
`docs/tex/` is treated as code. Cite these texts where they carry the material, and state any deviation from their standard algorithms explicitly. The core references are a routing table, grouped by what they inform:

**Infrastructure (Build, Structure, and Speed)**
*   **Software Craft:** Martin (*Clean Code*); Blandy et al. (*Programming Rust*)
*   **Systems & Hardware:** Bryant & O'Hallaron (*Computer Systems*); Hwu et al. (*Programming Massively Parallel Processors*)

**Optimization (Discrete and Continuous)**
*   **Algorithms & Math:** Cormen et al. (*Introduction to Algorithms*); Rosen (*Discrete Mathematics and Its Applications*)
*   **Numerical Optimization:** Nocedal & Wright (*Numerical Optimization*)
*   **Probabilistic Inference:** MacKay (*Information Theory...*); Koller & Friedman (*Probabilistic Graphical Models*); Frey (*Graphical Models...*); Ortega (*Introduction to Graph Signal Processing*)
*   **Statistical Physics:** Mézard & Montanari (*Information, Physics, and Computation*); Newman & Barkema (*Monte Carlo Methods in Statistical Physics*)
*   **Information Geometry:** Amari (*Information Geometry and Its Applications*)
*   **Learning & RL:** Goodfellow et al. / Prince (*Deep Learning*); Sutton & Barto (*Reinforcement Learning*); Lapan (*Deep RL Hands-On*); Raschka (*Build a Large Language Model*)

**Application (The Science)**
*   **Phylogenetics:** Felsenstein (*Inferring Phylogenies*); Durbin et al. (*Biological Sequence Analysis*); Compeau & Pevzner (*Bioinformatics Algorithms*); Pachter & Sturmfels (*Algebraic Statistics for Computational Biology*)
*   **Information/Quantum:** Blahut (*Algebraic Codes for Data Transmission*); Nielsen & Chuang (*Quantum Computation and Quantum Information* — background only)

## Definition of Done
1.  **Regression Test:** Asserts scientific validity (not just shape/execution/coverage theatre) and pins expected output.
2.  **Benchmark:** New/changed hot functions include a `pytest-benchmark` (Python) or `criterion` bench (Rust). Baseline numbers reported in PR.
3.  **Coverage:** `--cov-fail-under` gate is maintained or raised. Never lower it to pass a PR.
4.  **Docs & Tooling:** CI covers the new code. `ruff`, `mypy`, and `cargo` checks pass locally. Documentation Sync above is satisfied.
5.  **Dependency Hygiene:** Follows OSI-license and external tools rules.

## Dependencies & External Tools
*   Must be open source (OSI-approved license).
*   Ask for explicit permission before adding new tools/dependencies.
*   Flag any proposed dependency with $<1,000$ GitHub stars (or equivalent ecosystem metric) for explicit review.
