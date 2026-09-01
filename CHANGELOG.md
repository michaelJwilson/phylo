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

### Changed

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

### Fixed

- CI's `lint` job installed only the `dev` extra while `mypy` checks
  `tests/`, so every run failed on unresolvable `numpy` and `pytest`
  imports. It now installs `dev` and `test`.
- CI's Rust audit built `cargo-audit` from a floating resolve, which broke
  when a transitive dependency raised its minimum `rustc` above the pinned
  1.94.1. It now installs with `--locked`, at a pinned version, from a cache.

### Security

- Raised the `pytest` floor to `>=9.0.3` for PYSEC-2026-1845. The previous
  `<9` cap made the fixed version unreachable.
