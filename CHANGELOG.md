# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). This project has
not made a tagged release yet — everything so far lives under `[Unreleased]`.

## [Unreleased]

### Added

- Project scaffolding: `uv`-based environment setup (Python 3.12).
- Rust backend via `maturin`/PyO3, importable as `phylo.oxiphylo` (currently
  one example binding, `double`).
- `run_phylo` console-script entry point (placeholder).
- Python test suite: fixed-input regression tests and a `pytest-benchmark`
  suite (`tests/`), gated on a minimum coverage threshold in CI.
- Rust test suite: `cargo test` unit tests and a `criterion` benchmark
  (`benches/`).
- Sphinx API docs (`docs/`), built in CI with warnings as errors.
- Technical document (`docs/tex/`): a LaTeX PDF covering the substitution
  model, the Felsenstein likelihood and pruning algorithm, simulation, tree
  search with NNI and SPR move sets, gradients, the reinforcement-learning
  formulation, and the computational structure behind them. Built in CI,
  which fails on undefined references or citations.
- GitHub Actions CI, required on every PR: Python lint/type-check (`ruff`,
  strict `mypy`), Rust lint/format (`clippy`, `cargo fmt`), Rust tests +
  benchmark, a combined Python/Rust build check, the Python test suite, the
  docs build, and dependency audits.
- Dependency audits: `pip-audit` and `cargo audit`, in CI and as pre-commit
  hooks.
- `pre-commit` configuration mirroring the CI checks for local use.
- MIT license; single-source-of-truth versioning (`pyproject.toml` reads the
  package version from `Cargo.toml` via maturin's dynamic-version support).
- Locked, reproducible environments: `uv.lock` alongside `Cargo.lock`, a
  pinned Rust toolchain (`rust-toolchain.toml`), and a pinned CI runner image
  and `uv` version. Every CI install uses `--locked`.
- The four module directories are packages: `sim/`, `likelihood/`, `opt/`, and `search/` each have an `__init__.py`, so their `CLAUDE.md` loads when a session works in them and `DEV.md`'s layout table is true.
- `.github/pull_request_template.md`: a Definition-of-Done checklist mirroring `CLAUDE.md`'s five items, a benchmark-numbers slot, and a Documentation Sync line, so the exit of a PR carries the same reminders the intake issue template already does. A template, not a CI gate — `DEV.md` records that every PR starts from it.

### Changed

- CI caches the `uv` environment (`lint`, `python-tests`, `docs`) and the Cargo registry plus the `oxiphylo` `target/` build (`rust-lint`, `rust-tests`, `build`, and those same three jobs), keyed on `uv.lock` and `Cargo.lock` respectively, so the six jobs that install both toolchains stop doing it cold and the extension stops recompiling three times per PR.

- Doc reorganization for structural infra/application separation (#32):
  dropped the explicit `Domain`/`Axis` label columns from `DEV.md`'s
  repository-layout table and `README.md`'s documentation table, and
  reordered both tables and `DEV.md`'s top-level sections
  infrastructure-first, application-last, so file placement and ordering
  carry the domain instead of a narrated label. `infra/`, the per-module
  `CLAUDE.md` files, `.pre-commit-config.yaml`, and `.github/workflows/ci.yml`
  were audited and confirmed free of phylogenetic assumptions outside the
  two expected application hooks (`--cov=phylo`, the `oxiphylo` smoke
  import).

- Documentation split by audience: `README.md` is an overview, `INSTALL.md`
  covers installing and working locally, `DEV.md` covers repository layout,
  CI, and conventions, and `ROADMAP.md` states the long-term scientific goal.
- `mypy` now runs in `strict` mode over `python/` and `tests/`, so an
  unannotated signature fails CI.
- Tests are linted like the rest of the repo; ruff's blanket `"tests/**" =
  ["ALL"]` exemption is gone.
- Benchmarks seed via `np.random.default_rng` rather than the legacy global
  `np.random.seed`, and ruff's `NPY002` now enforces that.
- CI audits only the dependency graphs that changed: a marker keyed on the
  hash of `uv.lock` and `Cargo.lock` skips the `audit` job's work when that
  exact graph already passed. The key carries the ISO week, and a weekly
  scheduled run audits `main`, so advisories disclosed against unchanged
  pins still surface.
- Reference sources are grouped by infrastructure and application, and by
  topic within each, growing from 6 texts to 25. The technical document
  gains a `Sources` section carrying the same taxonomy, and cites every
  entry.
- `ROADMAP.md` and the technical document gain three extensions to the move
  set: bounds that rule out whole sets of trees, learned compound moves
  drawn from a Dirichlet process, and a transformer policy over compressed
  Newick strings. All three are proposals, and milestone 9 records what
  would settle them.
- `ROADMAP.md` gains a six-workstream breakdown — simulate, compress, fit,
  move, track, benchmark — each with completion criteria and its main risk,
  and the milestone table now maps to it. The move-set entry separates
  connectivity from optimality, tabulates NNI, SPR, and multi-SPR against
  both, and proposes TBR, stochastic escape, guided restriction,
  recombination, and exhaustive search as additions.
- The technical document states two algorithms it previously left implicit:
  a canonical Newick form that fixes rooting and child order, which settles
  the encoding for the transformer policy and supplies the memoization key
  for search, and the closed-form `k`-state Jukes–Cantor transition
  probabilities, which give the simulator an oracle independent of the
  likelihood code.
- `ROADMAP.md` states requirements: problem size (`n` 10–1000, `L`
  100–10 000, general `k`), accuracy (normalized RF ≤ 0.05, `Δ ln L`
  competitive with IQ-TREE 2 and RAxML-NG at equal wall clock), runtime
  (sub-second gradient updates at `n = 100`, amortized search), memory
  (`O(n × L × k)` within 16 GB unified or 24 GB GPU), hardware (CUDA and
  Metal both first-class, with an efficient CPU path), and a cross-device
  numerical tolerance policy.
- `pre-commit` no longer runs `pip-audit` and `cargo audit`. They reach the
  network and build `cargo-audit`, which is too slow for every commit; CI
  runs them when a lockfile changes and weekly on `main`.
- CI cancels a branch's superseded runs instead of paying for both. `main`
  is excluded, since its runs populate the audit caches PRs restore from.
- `DEV.md` records the GitHub settings CI depends on but which live outside
  the repository — branch auto-deletion, protection rules, required checks,
  token permissions — and the CI budget rules: cap test sizes, never rank
  performance on shared runners, release-gate long tests.
- Module skeleton: `sim/`, `likelihood/`, `opt/`, `search/`, and `infra/`,
  each carrying a `CLAUDE.md` for the concerns local to it — the analytic
  oracle simulation validates against, the cross-device tolerance policy and
  NumPy reference the likelihood keeps, constraint handling in the optimizer,
  the `n <= 10` bound on topological tests, and the CI limits, tracking
  manifest, and ticket policy in `infra/`. No code yet: the directories
  declare where work goes and under what rules.
- Framework decisions recorded: **PyTorch** for autodiff (mature MPS backend
  on Apple Silicon alongside CUDA) and **Aim** for experiment tracking (open
  source, self-hostable). Neither is added to `pyproject.toml` until code
  imports it.
- Robinson–Foulds distance will be implemented in-repo and tested against
  hand-computed cases; an external implementation is noted as a future
  cross-check rather than adopted as a dependency.
- `STATUS.md`: coverage of every planned item — done, planned, in an open
  PR, or untouched — standing in for a project board, with the rule that
  the PR changing an item's status updates its row. Records three live
  cross-document inconsistencies: the reward is defined twice and
  differently, the cross-device tolerance policy states no number, and an
  accuracy target names baseline tools nothing can currently run.
- `DEV.md` and `INSTALL.md` separate portable infrastructure from
  phylogenetics-specific guidance, and `README.md`'s documentation map records
  which axis each document sits on.
- Guidance is no longer duplicated across files. Root `CLAUDE.md` gained the infrastructure/application split, a map of the other documents, and the two decisions that were stranded in submodule files (PyTorch, the cross-device tolerance policy); the submodule `CLAUDE.md` files keep only what is local to them. `STATUS.md` absorbed `CLAUDE.md`'s "Known Gaps" as a Scaffolding gaps section, so one ledger carries the rule that keeps it accurate.

### Fixed

- CI's `lint` job installed only the `dev` extra while `mypy` checks
  `tests/`, so every run failed on unresolvable `numpy` and `pytest`
  imports. It now installs `dev` and `test`.
- CI's Rust audit built `cargo-audit` from a floating resolve, which broke
  when a transitive dependency raised its minimum `rustc` above the pinned
  1.94.1. It now installs with `--locked`, at a pinned version, from a cache.

### Removed

- Changelog fragments (`changelog.d/`) and the CI enforcement around them.
  `CHANGELOG.md` is now a plain, manually-edited file under `[Unreleased]`;
  the fragment-per-PR assembly step (`infra/changelog.py`) and its
  `--check`/`--assemble` CI steps are gone.

### Security

- Raised the `pytest` floor to `>=9.0.3` for PYSEC-2026-1845. The previous
  `<9` cap made the fixed version unreachable.
