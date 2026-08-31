# phylo

[![CI](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`phylo` is a high-performance scientific Python package with an optional
Rust-accelerated backend (`phylo.oxiphylo`, via
[PyO3](https://pyo3.rs)/[maturin](https://www.maturin.rs)).

## Setup

```
# Create the virtual environment
uv venv --python 3.12

# Activate the environment
# On macOS/Linux:
source .venv/bin/activate 
```

## Building

The package uses `maturin` as its PEP 517 build backend, so a normal install
compiles the Rust extension:

```
pip install .
```

This makes `phylo.oxiphylo` (currently one example binding, `double`)
importable from Python.

## Tests

```
pip install ".[test]"
pytest      # Python: regression tests (tests/regression), property-based
            # tests (tests/properties), a pytest-benchmark suite
            # (tests/benchmarks), and an integration test that the Rust
            # extension imports correctly (tests/test_oxiphylo_bindings.py)
cargo test  # Rust: unit tests for the PyO3 bindings (src/lib.rs)
cargo bench # Rust: Criterion benchmarks (benches/)
```

## Linting & type checking

```
pip install ".[dev]"
ruff check .
ruff format --check .
mypy python/
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

Python code in this repo is type-hinted; `mypy` is the enforcement point
for that (ruff's annotation-presence rules are intentionally off — see
`CLAUDE.md`). Optionally run `pre-commit install` after `pip install
".[dev]"` to run all of the above automatically on `git commit`.

## Documentation

API docs are built with Sphinx (`sphinx.ext.autodoc` + `napoleon`, which
parses the NumPy-style docstrings used in this repo):

```
pip install ".[docs]"
sphinx-build -b html docs/source docs/_build/html
```

Open `docs/_build/html/index.html`. CI builds these docs with `-W`
(warnings treated as errors) on every PR, so a broken docstring or a Sphinx
warning fails the build rather than shipping silently.

## Continuous integration

Every pull request against `main` runs six GitHub Actions jobs
(`.github/workflows/ci.yml`) ahead of review: `lint` (`ruff check`, `ruff
format --check`, `mypy`), `rust-lint` (`cargo clippy`, `cargo fmt --check`),
`rust-tests` (`cargo test` and `cargo bench`), `build` (compiles the
extension and smoke-imports `phylo.oxiphylo`), `python-tests` (the full
`pytest` suite, including the `hypothesis` property tests, gated on a
minimum coverage threshold via `pytest-cov`), and `docs` (the Sphinx build
above, with warnings as errors).

## Versioning

The package version lives in one place, `Cargo.toml`'s `[package].version`;
`pyproject.toml` declares it `dynamic` and maturin reads it from there, so
the two can't silently drift out of sync.

## License

MIT — see [LICENSE](LICENSE).

## Development approach

The Rust backend scaffold and the Python test/benchmark harness were
independent pieces of work touching disjoint files, so they were built by
two sub-agents running in parallel — each in an isolated git worktree, each
opening its own PR. The follow-up work (renaming the extension to
`oxiphylo`, adding Rust-side tests, and wiring up CI across both stacks)
touched both halves at once, so it was done sequentially in a single PR
instead of another parallel split — see `CLAUDE.md` for when to prefer one
approach over the other.
