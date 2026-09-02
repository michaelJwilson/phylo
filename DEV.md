# Developing phylo

This document outlines repository structure, CI enforcement, and contribution rules. For setup, see `INSTALL.md`; for project trajectory, see `ROADMAP.md`. **`CLAUDE.md` is the authoritative source for conventions; in any conflict, `CLAUDE.md` prevails.**

## Repository Layout

Infrastructure paths first, application paths after — the grouping below
carries the domain; `CLAUDE.md` states why keeping it liftable matters.

| Path | Contents |
| --- | --- |
| `benches/`, `tests/` | Criterion benchmarks (Rust), pytest suite, and integration tests. |
| `docs/source/` | Sphinx API documentation. |
| `python/phylo/` | Python package: re-exports, typed extension stubs, stub CLI. |
| `python/phylo/sim/` | Data generation and ground-truth retention. |
| `python/phylo/likelihood/` | Felsenstein pruning; CPU, CUDA, and Metal dispatch. |
| `python/phylo/opt/` | Continuous parameter fitting via autodiff (PyTorch). |
| `python/phylo/search/` | Move sets, RL agents, temperature schedules. |
| `src/lib.rs` | Rust extension (`oxiphylo`), exposed through PyO3. |
| `docs/tex/` | LaTeX source for the technical document. |

*Note: Each directory contains a localized `CLAUDE.md` defining specific constraints (e.g., `sim/` oracles, `search/` constraints). These append to, rather than override, the root `CLAUDE.md`.*

---

## Infrastructure & Tooling

### Build System

`maturin` builds the Rust extension natively during `pip install .`.

* **Requirement:** A Rust toolchain is required for consumers.
* **Known Gap:** The typed stub `python/phylo/oxiphylo.pyi` is hand-written. Run `python -m mypy.stubtest phylo.oxiphylo` periodically to prevent drift.

### Continuous Integration

Eight required checks run via GitHub Actions (`.github/workflows/ci.yml`) on PRs against `main`:

| Job | Execution |
| --- | --- |
| `lint` | `ruff check`, `ruff format --check`, strict `mypy` |
| `rust-lint` | `cargo clippy -D warnings`, `cargo fmt --check` |
| `rust-tests` | `cargo test --locked`, `cargo bench` (informational) |
| `build` | `pip install .` (no lockfile, mimics fresh consumer), smoke import |
| `python-tests` | `pytest` suite, gated on minimum coverage |
| `docs` | Sphinx build (warnings as errors) |
| `technical-doc` | LaTeX build (fails on undefined refs/citations) |
| `audit` | `pip-audit`, `cargo audit` (skips on cache hit if lockfiles are unchanged) |

`lint`, `python-tests`, and `docs` restore a `~/.cache/uv` cache keyed on `uv.lock`'s hash before installing `uv`. `rust-lint`, `rust-tests`, `build`, and those same three jobs restore a shared `~/.cargo/registry`, `~/.cargo/git`, and `target/` cache keyed on `Cargo.lock`'s hash, so `oxiphylo` (built via `maturin`/`pyo3` on every `uv sync` or `pip install .`) compiles from scratch only when a lockfile changes or no job has populated the cache yet. `audit`'s per-week marker cache (above) is unrelated and unaffected.

### CI & Performance Budget

* **Size Caps:** Restrict topological move tests to $n \le 10$ (exhaustive enumeration oracle).
* **No CI Profiling:** Do not rank performance on GitHub runners due to hardware variance. Benchmark on fixed hardware.
* **Release-Gated:** Long-running scientific validity tests run on release, not per PR.
* **Concurrency:** Superseded CI runs on the same branch are automatically cancelled.

### Core Development Standards

* **Reproducibility:** Pin environments entirely. Use `--locked` for CI installs, pin runner images (`ubuntu-24.04`), and strictly use `np.random.default_rng(seed)`.
* **Versioning:** Maintained strictly in `Cargo.toml` (`[package].version`).
* **Definition of Done:** Follow `CLAUDE.md`'s checklist. A PR must also update the item's status in `STATUS.md`.
* **PR Template:** Every PR starts from `.github/pull_request_template.md`, which carries the Definition-of-Done checklist, a benchmark-numbers slot, and a Documentation Sync line as a reminder, not a CI gate.
* **Agentic Approach:** Use parallel git worktrees/PRs for disjoint tasks. Use single sequential PRs for coupled changes.

### Dependency Management

1. **Request:** Explicitly request permission before adding dependencies/tools.
2. **Validate:** Must use OSI-approved licenses. Flag items with $<1000$ GitHub stars.
3. **Lock:** Run `uv lock` or update `Cargo.lock` and commit in the same PR.
4. **Justify:** Explain the inclusion in the PR description.

---

## Application Standards

### Performance

Accelerate hot paths via GPU (PyTorch/Triton/JAX) *only* if benchmarking proves a $\ge 10x$ speedup over vectorized NumPy at realistic sizes. Otherwise, use Rust. The pure Python implementation must be retained as a pinned regression oracle.

### Testing

Assert scientific validity. Generate fixtures via component-wise simulation under known generative models. Shape-only or runs-without-raising assertions are strictly forbidden.

### Technical Document

`docs/tex/` is versioned as code. Update it in the same PR that alters a model, equation, algorithm, or QA figure.
