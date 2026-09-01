# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project
`phylo` is a high-performance scientific repository. Correctness and reproducibility of numerical/scientific results take priority over convenience.

## Environment & Tooling
*   **Python (3.12):** Manage via `uv`. Run `uv sync --locked --all-extras`. Regenerate locks with `uv lock` and commit `uv.lock` in the same PR.
*   **Rust:** Compiler pinned via `rust-toolchain.toml`. Lockfile is `Cargo.lock`. Update with `cargo update` and commit.
*   **Lint/Format (Python):** `ruff check .` and `ruff format --check .`
*   **Type Check (Python):** `mypy --strict` on `python/` and `tests/`.
*   **Lint/Format (Rust):** `cargo clippy --all-targets -- -D warnings` and `cargo fmt --check`.
*   **Audit:** `pip-audit` (Python) and `cargo audit` (Rust).
*   **Docs:** Build with `sphinx-build -W` in `docs/source/`.

## Conventions
*   **Hot Paths:** Prefer vectorized implementations over pure Python (see Performance).
*   **Documentation Sync:** Any change affecting behavior, CI, dev setup, or math models must update `README.md`, `CLAUDE.md`, `CHANGELOG.md` (if user-visible), and/or `docs/tex/` in the same PR.
*   **Single Version Source:** The package version lives exclusively in `Cargo.toml`'s `[package].version`.
*   **Code Standards:** Use type hints on all Python functions. Do not introduce silent behavior changes (e.g., default parameters). Keep dependencies minimal and justify additions.

## Performance
*   **GPU (PyTorch, Triton, JAX):** Target if the hot path is data-parallel and earns $\ge 10\times$ speedup over vectorized NumPy at realistic problem sizes.
*   **Rust Backend (`oxiphylo`):** Target for CPU-bound hot paths (control flow, tree traversal, irregular memory access, small sizes).
*   **Measurement:** Benchmark candidates against the NumPy reference before committing to a port. Report both numbers in the PR.
*   **The Oracle:** Every accelerated kernel keeps its pure Python/NumPy implementation as an oracle. Regression tests must pin the accelerated output against it within an explicit tolerance.

## Testing & Quality Assurance
*   **Simulate Component-Wise:** Build fixtures by simulating from a known generative model with an explicitly seeded generator (`np.random.default_rng(seed)`). Test components individually.
*   **Pin to Independent Sources:** Validate expected values against analytic results, brute-force computations, or secondary implementations with stated tolerances.
*   **Check Math Invariants:** Ensure rows of transition matrices sum to 1, models satisfy detailed balance, gradients match finite differences, and likelihood increases monotonically.
*   **No Coverage Theatre:** Tests asserting only output shapes or successful execution without exceptions are forbidden. Leave gaps unwritten and log them in "Known Gaps" rather than writing meaningless tests.
*   **Scientific Outputs:** The suite must emit plots and tables for the LaTeX technical document. Update the LaTeX captions concurrently.

## Technical Document & Reference Sources
`docs/tex/` is treated as code. Cite these texts and explicitly state any deviations from their standard algorithms:
*   Hwu, Kirk & El Hajj: *Programming Massively Parallel Processors*
*   MacKay: *Information Theory, Inference, and Learning Algorithms*
*   Goodfellow et al. / Prince: *Deep Learning* / *Understanding Deep Learning*
*   Sutton & Barto: *Reinforcement Learning: An Introduction*
*   Felsenstein: *Inferring Phylogenies*

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
4.  **Docs & Tooling:** CI covers the new code. `ruff`, `mypy`, and `cargo` checks pass locally.
5.  **Dependency Hygiene:** Follows OSI-license and external tools rules.

## Dependencies & External Tools
*   Must be open source (OSI-approved license).
*   Ask for explicit permission before adding new tools/dependencies.
*   Flag any proposed dependency with $<1,000$ GitHub stars (or equivalent ecosystem metric) for explicit review.

## Known Gaps
*   **No real science:** 100% coverage is currently a smoke test on placeholder functions (`double`, `pairwise_distance`).
*   **Invalid test patterns:** Current benchmark/CLI tests assert only shapes or print statements.
*   **Missing QA framework:** Component-wise simulated fixtures and plot generation do not exist yet.
*   **Rust backend inactive:** No numerical function is currently accelerated in `oxiphylo`.
*   **No module structure:** `python/phylo/` lacks a `core.py` equivalent.
*   **Missing CI:** No performance regression detection, no multi-platform/version tests (currently only 3.12/Ubuntu), no distributable wheel artifacts.
*   **Stub drift:** `oxiphylo.pyi` is unchecked (`python -m mypy.stubtest` needed).

## Working with Sub-Agents
*   **Parallel:** Use isolated git worktrees/PRs for disjoint tasks (e.g., Rust extension scaffold vs. Python test harness).
*   **Sequential:** Keep coupled work in a single thread to avoid context-derivation overhead and merge conflicts.
