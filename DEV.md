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
| `python/phylo/likelihood/` | Felsenstein pruning; CPU dispatch landed (NumPy, PyTorch, Rust), CUDA and Metal dispatch not yet implemented. Also the phylogenetic `Objective` (`objective.py`), which adapts the recursion to `opt/`'s fitting interface — it is here because `opt/` may import no application module. |
| `python/phylo/opt/` | Model-agnostic continuous parameter fitting via autodiff (PyTorch): the `Objective` interface, shared constraint maps, and the Potts and HMM reference instances. Imports nothing from `sim/`, `likelihood/` or `search/`, asserted by test. |
| `python/phylo/search/` | Move sets, RL agents, temperature schedules. |
| `python/phylo/qa/` | QA figures/tables for the technical document; renders, doesn't recompute. |
| `src/lib.rs` | Rust extension (`oxiphylo`), exposed through PyO3. |
| `docs/tex/` | LaTeX source for the technical document. |
| `infra/build_technical_doc.sh` | Regenerates QA figures, then builds `docs/draft.pdf` (committed). |

*Note: Each directory contains a localized `CLAUDE.md` defining specific constraints (e.g., `sim/` oracles, `search/` constraints). These append to, rather than override, the root `CLAUDE.md`.*

New issues are filed through `.github/ISSUE_TEMPLATE/task.yml`; blank issues are disabled via `.github/ISSUE_TEMPLATE/config.yml`.

## Test Layout

`tests/` is organized by **kind** at the top level and by subject within it. Where a new test goes follows from what kind of check it is, not from what it covers.

| Path | Holds |
| --- | --- |
| `tests/regression/` | Correctness. Asserts scientific validity against an independent oracle. |
| `tests/benchmarks/` | `pytest-benchmark` timings. Asserts shape only; correctness is pinned by the regression counterpart. |
| `tests/regression/fixtures/` | Declarative test data (e.g. `simulation_params.yaml`). Data, not Python. |
| `tests/` (top level) | Whole-package and binding smoke tests, which belong to no single kind or submodule — `test_run_phylo.py`, `test_oxiphylo_bindings.py`. |

* **Every benchmark pairs with a regression module.** `benchmarks/test_<name>_bench.py` accompanies `regression/test_<name>.py`. A benchmark without a counterpart asserts nothing about correctness, which `CLAUDE.md`'s "No Coverage Theatre" rule forbids.
* **Split by submodule only when a kind outgrows one flat directory** — a future `tests/regression/likelihood/`, not a top-level `tests/likelihood/`. Kind stays the outer axis; a subject-first split would fight the two directories already there.
* **Fixtures follow their blast radius.** Used by one module: keep it in that module, or in a local `conftest.py`. Shared across modules: a top-level underscore-prefixed module such as `tests/_example_hotpath.py`, which is imported rather than collected.

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
| `lint` | `ruff check`, `ruff format --check`, strict `mypy`, `towncrier check` |
| `rust-lint` | `cargo clippy -D warnings`, `cargo fmt --check` |
| `rust-tests` | `cargo test --locked`, `cargo bench` (informational) |
| `build` | `pip install .` (no lockfile, mimics fresh consumer), smoke import |
| `python-tests` | `pytest -m "not release"`, gated on minimum coverage; benchmarks skipped unless computational code changed |
| `docs` | Sphinx build (warnings as errors) |
| `technical-doc` | Regenerate QA figures (`infra/build_technical_doc.sh`), then LaTeX build (fails on undefined refs/citations, or if the rebuilt `docs/draft.pdf` differs from the committed one) |
| `audit` | `pip-audit`, `cargo audit` (skips on cache hit if lockfiles are unchanged) |

`lint`, `python-tests`, and `docs` restore a `~/.cache/uv` cache keyed on `uv.lock`'s hash before installing `uv`. `rust-lint`, `rust-tests`, `build`, and those same three jobs restore a shared `~/.cargo/registry`, `~/.cargo/git`, and `target/` cache keyed on `Cargo.lock`'s hash, so `oxiphylo` (built via `maturin`/`pyo3` on every `uv sync` or `pip install .`) compiles from scratch only when a lockfile changes or no job has populated the cache yet. `audit`'s per-week marker cache (above) is unrelated and unaffected.

### CI & Performance Budget

* **Size Caps:** Restrict topological move tests to $n \le 10$ (exhaustive enumeration oracle).
* **No CI Profiling:** Do not rank performance on GitHub runners due to hardware variance. Benchmark on fixed hardware.
* **Release-Gated:** Long-running scientific validity tests run on release, not per PR. Mark them `@pytest.mark.release` (registered in `pyproject.toml`).
  * **Use `pytest -m "not release"` while developing.** That is what CI's `python-tests` job runs, so it is the gate a PR is actually judged against. Do not run the full suite to check ordinary work.
  * **The full suite is expensive and its cost is not obvious from the test count.** Measured on one development machine on the same checkout: `pytest -m "not release"` took 131 s over 140 tests; plain `pytest` took 954 s over 141 — one extra test, roughly 7x the wall clock. Exhaustive topological tests dominate, and they grow combinatorially with taxon count.
  * **Plain `pytest` (no `-m` filter) is the release gate's job, not a development command.** `infra/release.sh` runs it as part of cutting a release; run it by hand only when you are cutting one, or when you have changed a release-gated test itself.
* **Benchmarks are conditional.** They are half the suite's wall clock (36 s of 71 s) and measure code a docs or QA change cannot have altered, so `python-tests` runs them only when the diff against the base branch touches `src/`, `python/phylo/{sim,likelihood,opt,search}/`, `tests/benchmarks/`, or a lockfile or project file. The job itself always runs and always reports — it is a required check, and skipping the job rather than the step would leave it pending and block the merge. Coverage is unaffected, because every line a benchmark reaches is also reached by the regression module it pairs with.
* **Tolerances on a quantity that scales with problem size are relative.** The log-likelihood is a sum over sites, so an absolute bound fixed at one site count does not transfer to another: the backends agree to ~8e-13 relative at every size, but that same agreement is 7.4e-07 absolute at 200,000 sites. Absolute bounds are correct for quantities that do not scale — a transition probability, a row sum, a Monte Carlo frequency — and are kept there.
* **Concurrency:** Superseded CI runs on the same branch are automatically cancelled.

### Core Development Standards

* **Reproducibility:** Pin environments entirely. Use `--locked` for CI installs, pin runner images (`ubuntu-24.04`), and strictly use `np.random.default_rng(seed)`.
* **Versioning:** Maintained strictly in `Cargo.toml` (`[package].version`).
* **Definition of Done:** Follow `CLAUDE.md`'s checklist.
* **PR Template:** Every PR starts from `.github/pull_request_template.md`, which carries the Definition-of-Done checklist, a benchmark-numbers table, a second Benchmark-section table for the realized value of any scientific/tolerance regression test the PR touches (test, reference, tolerance, realized value — write "N/A" as text and delete the table if none), a Documentation Sync line, and a Follow-up / Deferred Work section for TODOs left to a tracking issue, all as a reminder, not a CI gate.
* **Agentic Approach:** Use parallel git worktrees/PRs for disjoint tasks. Use single sequential PRs for coupled changes.

### Dependency Management

1. **Request:** Explicitly request permission before adding dependencies/tools.
2. **Validate:** Must use OSI-approved licenses. Flag items with $<1000$ GitHub stars.
3. **Lock:** Run `uv lock` or update `Cargo.lock` and commit in the same PR.
4. **Justify:** Explain the inclusion in the PR description.

### Release

A release is cut from a Release-template issue (`.github/ISSUE_TEMPLATE/release.yml`):
it drives the repository-consolidation audit (roadmap progress, doc/code
consistency, duplicated machinery, suggested follow-up tickets) and gates on
`infra/release.sh` passing before a maintainer adds the `release` label.

1. **Run the gate.** `infra/release.sh` runs every per-PR CI check
   (`ruff check`, `ruff format --check`, `mypy --strict`, `cargo clippy -D
   warnings`, `cargo fmt --check`, `cargo test --locked`) plus what CI skips
   per PR: the full `pytest` suite including `@pytest.mark.release` tests
   (see "Release-Gated" above), `sphinx-build -W`, and
   `infra/build_technical_doc.sh`. It runs every check regardless of earlier
   failures and prints a pass/fail summary at the end; a non-zero exit means
   at least one check failed.
2. **Bump the version.** Edit `[package].version` in `Cargo.toml` — the
   single version source (CLAUDE.md) — then run `cargo build` so
   `Cargo.lock`'s `oxiphylo` entry picks up the new version, and commit both.
   `maturin` reads the Python package version from the same field
   (`dynamic = ["version"]` in `pyproject.toml`), so nothing else needs
   editing.
3. **Build the changelog.** Run `uv run towncrier build --version
   <version>` from the repository root: it consumes every fragment in
   `changelog.d/`, deletes them, and inserts a dated `## [<version>]` section
   into `CHANGELOG.md` (see `changelog.d/README.md`). Commit the result.
4. **Tag and publish.** Open a PR with the version bump and changelog
   commit; once merged, tag the merge commit (`git tag v<version> && git
   push origin v<version>`) and publish a GitHub release from that tag,
   with the new `CHANGELOG.md` section as its body.

**Worked example (first release, `0.1.0`):** `Cargo.toml` and `Cargo.lock`
already carry `0.1.0` with no `v0.1.0` tag yet, so step 2 is a no-op check
rather than an edit. `infra/release.sh` passing clean plus the
consolidation checklist above is what the Release-template issue is
gating on before step 3–4 cut the tag.

---

## Application Standards

### Performance

Accelerate hot paths via GPU (PyTorch/Triton/JAX) *only* if benchmarking proves a $\ge 10x$ speedup over vectorized NumPy at realistic sizes. Otherwise, use Rust. The pure Python implementation must be retained as a pinned regression oracle.

### Testing

Assert scientific validity. Generate fixtures via component-wise simulation under known generative models. Shape-only or runs-without-raising assertions are strictly forbidden.

### Technical Document

`docs/tex/` is versioned as code. Update it in the same PR that alters a model, equation, algorithm, or QA figure. `docs/draft.pdf` is committed, not just built: regenerate it with `infra/build_technical_doc.sh` and commit the result in that same PR. CI's `technical-doc` job fails if the committed PDF is stale.
