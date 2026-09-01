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

- `mypy` now runs in `strict` mode over `python/` and `tests/`, so an
  unannotated signature fails CI.
- Tests are linted like the rest of the repo; ruff's blanket `"tests/**" =
  ["ALL"]` exemption is gone.
- Benchmarks seed via `np.random.default_rng` rather than the legacy global
  `np.random.seed`, and ruff's `NPY002` now enforces that.

### Security

- Raised the `pytest` floor to `>=9.0.3` for PYSEC-2026-1845. The previous
  `<9` cap made the fixed version unreachable.
