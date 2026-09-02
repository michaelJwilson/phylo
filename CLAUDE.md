# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project
`phylo` is a high-performance scientific repository. Correctness and reproducibility of numerical/scientific results take priority over convenience.

Two separable things live here, and keeping them separable is a constraint rather than an observation:

*   **Infrastructure:** the build, the checks, the release process, the agentic workflow. None of it mentions phylogenetics; all of it would transplant to an unrelated scientific project unchanged.
*   **Application:** substitution models, likelihoods, tree search, and the standards that make claims about them credible. Specific to this science.

An infrastructure rule that acquires a phylogenetic assumption stops being liftable; an application rule hidden in build configuration stops being reviewable by someone who knows the science. `DEV.md` and `README.md` carry this structurally — infrastructure content ordered before application content, rather than labeled row by row — and file placement (`infra/` vs. `python/phylo/*`, `docs/tex/`) does the rest.

## Repository Map
This file is authoritative. The rest exist so it does not have to carry everything, and each has one job:

| Document | Job |
| --- | --- |
| `README.md` | What the project is, and where everything else lives |
| `INSTALL.md` | Installing, building, running the tests locally |
| `DEV.md` | Layout, the CI jobs, repository settings, the CI budget, how a change is reviewed |
| `ROADMAP.md` | The scientific goal, requirements, and milestones |
| `CHANGELOG.md` | What has landed, per dated release section; built from `changelog.d/` fragments by `towncrier` |
| `docs/tex/` | The technical document: background, equations, algorithms |

`python/phylo/sim/`, `likelihood/`, `opt/`, `search/`, `qa/`, and `infra/` each carry their own `CLAUDE.md`. Those add what applies only inside one module; they never override this file. A rule that binds the whole repository belongs here, not in one of them.

## Environment & Tooling
*   **Python (3.12):** Manage via `uv`. Run `uv sync --locked --all-extras`. Regenerate locks with `uv lock` and commit `uv.lock` in the same PR.
*   **Rust:** Compiler pinned via `rust-toolchain.toml`. Lockfile is `Cargo.lock`. Update with `cargo update` and commit.
*   **Lint/Format (Python):** `ruff check .` and `ruff format --check .`
*   **Type Check (Python):** `mypy --strict`, over the paths in `pyproject.toml`'s `files` (`python/`, `tests/`).
*   **Lint/Format (Rust):** `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check`.
*   **Audit:** `pip-audit` (Python) and `cargo audit` (Rust).
*   **Docs:** Build with `sphinx-build -W` in `docs/source/`.

## Conventions
*   **Hot Paths:** Prefer vectorized implementations over pure Python (see Performance).
*   **Documentation Sync:** Any change affecting behavior, CI, dev setup, or math models must update, in the same PR, whichever of these it makes untrue: `README.md`, `CLAUDE.md` (including a module's), `DEV.md`, `INSTALL.md`, `ROADMAP.md`, `docs/tex/`. If the change is user-visible, add a fragment under `changelog.d/` (see `changelog.d/README.md`) rather than editing `CHANGELOG.md` directly — `towncrier` merges fragments into `CHANGELOG.md` at release time, and CI's `towncrier check` enforces one exists.
*   **Single Version Source:** The package version lives exclusively in `Cargo.toml`'s `[package].version`.
*   **Package Surface:** `python/phylo/__init__.py` re-exports nothing beyond the package's own top-level utilities (currently `double`); import submodule contents explicitly (`from phylo.likelihood import ...`), not through the top-level namespace.
*   **Code Standards:** Use type hints on all Python functions. Do not introduce silent behavior changes (e.g., default parameters). Keep dependencies minimal and justify additions.

## Performance
*   **GPU (PyTorch, Triton, JAX):** Target if the hot path is data-parallel and earns $\ge 10\times$ speedup over vectorized NumPy at realistic problem sizes.
*   **Rust Backend (`oxiphylo`):** Target for CPU-bound hot paths (control flow, tree traversal, irregular memory access, small sizes).
*   **Autodiff:** **PyTorch**, decided. Its MPS backend is the mature path on Apple Silicon, which `ROADMAP.md` targets alongside CUDA. Not yet a dependency: it is added by the first PR whose code imports it.
*   **Measurement:** Benchmark candidates against the NumPy reference before committing to a port. Report both numbers in the PR.
*   **The Oracle:** Every accelerated kernel keeps its pure Python/NumPy implementation as an oracle. Regression tests must pin the accelerated output against it within an explicit tolerance.

## Testing & Quality Assurance
*   **Simulate Component-Wise:** Build fixtures by simulating from a known generative model with an explicitly seeded generator (`np.random.default_rng(seed)`). Test components individually.
*   **Pin to Independent Sources:** Validate expected values against analytic results, brute-force computations, or secondary implementations with stated tolerances.
*   **Check Math Invariants:** Ensure rows of transition matrices sum to 1, models satisfy detailed balance, gradients match finite differences, and likelihood increases monotonically.
*   **Cross-Device Agreement Is a Tolerance:** `float32` and `float64` behave differently across CPU, CUDA, and Metal, and deep recursions accumulate that. Agreement is checked against a tolerance stated once in the technical document, never bitwise. A discrepancy inside it is not a bug and must not be "fixed".
*   **No Coverage Theatre:** Tests asserting only output shapes or successful execution without exceptions are forbidden. Leave gaps unwritten and track them as GitHub issues (`infra/TICKETING.md`) rather than writing meaningless tests.
*   **Scientific Outputs:** The suite must emit plots and tables for the LaTeX technical document. Update the LaTeX captions concurrently.

## Technical Document & Reference Sources
`docs/tex/` is treated as code. Cite these texts where they carry the material and explicitly state any deviations from their standard algorithms. The 25 core references are categorized as a routing table based on what they inform:

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

**Expected Reader:** a well-educated developer with scientific and performance-computing background, but not an application expert, e.g. phylogenetics. This sets the formatting contract for `docs/tex/`: keep the body streamlined — hyperlinks and citations over inline derivation — and push required application background (e.g. NNI, other standard algorithms) into a dedicated appendix, cited from the point of use rather than re-derived there. Treat the main text as a high-level overview of the current best-known approach (simulation, models) in terms of the roadmap, not an exhaustive record; link out to supporting docs, with plots, and results for dedicated studies that informed the technical doc.

## Writing Style
1.  **Be concise and direct:** Omit needless words, use active voice, and lead with the most important fact.
2.  **Be concrete and precise:** Use exact facts and numbers ("40% faster") instead of vague intensifiers ("much faster").
3.  **Stay neutral and objective:** Avoid marketing hype, subjective opinions, and weak qualifiers ("very", "rather").
4.  **Provide evidence:** Back every claim in PRs/commits with benchmark numbers, test outputs, or reproductions.
5.  **Maintain formatting:** Apply naming, terminology, and syntax consistently.

## Definition of Done
1.  **Regression Test:** Asserts scientific validity (not just shape/execution) and pins expected output.
2.  **Benchmark:** New/changed hot functions include a `pytest-benchmark` (Python) or `criterion` bench (Rust). Baseline numbers reported in PR.
3.  **Coverage:** `--cov-fail-under` gate is maintained or raised. Never lower it to pass a PR.
4.  **Docs & Tooling:** CI covers the new code. `ruff`, `mypy`, and `cargo` checks pass locally. Documentation Sync above is satisfied.
5.  **Dependency Hygiene:** Follows OSI-license and external tools rules.

## Dependencies & External Tools
*   Must be open source (OSI-approved license).
*   Ask for explicit permission before adding new tools/dependencies.
*   Flag any proposed dependency with $<1,000$ GitHub stars (or equivalent ecosystem metric) for explicit review.

## Known Gaps
GitHub issues and labels are the project board (`infra/TICKETING.md`): what exists, what is only recorded as intent, and what is untouched — including gaps in the current scaffolding — is tracked there, not in a second list in this repository. `ROADMAP.md` records milestone-level progress; file or update an issue for anything narrower.

## Working with Sub-Agents
*   **Parallel:** Use isolated git worktrees/PRs for disjoint tasks (e.g., Rust extension scaffold vs. Python test harness).
*   **Sequential:** Keep coupled work in a single thread to avoid context-derivation overhead and merge conflicts.
