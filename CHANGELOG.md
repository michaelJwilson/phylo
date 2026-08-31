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
- Python test suite: fixed-input regression tests, `hypothesis`
  property-based tests, and a `pytest-benchmark` suite (`tests/`), gated on
  a minimum coverage threshold in CI.
- Rust test suite: `cargo test` unit tests and a `criterion` benchmark
  (`benches/`).
- GitHub Actions CI, required on every PR: Python lint/type-check (`ruff`,
  `mypy`), Rust lint/format (`clippy`, `cargo fmt`), Rust tests + benchmark,
  a combined Python/Rust build check, and the Python test suite.
- `pre-commit` configuration mirroring the CI checks for local use.
- MIT license; single-source-of-truth versioning (`pyproject.toml` reads the
  package version from `Cargo.toml` via maturin's dynamic-version support).
