# phylo

[![CI](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`phylo` is a high-performance scientific Python package with an optional
Rust-accelerated backend (`phylo.oxiphylo`, via
[PyO3](https://pyo3.rs)/[maturin](https://www.maturin.rs)).

## Setup

```
# Create the environment from the lockfile
uv sync --locked --all-extras

# Activate the environment
# On macOS/Linux:
source .venv/bin/activate 
```

`--locked` fails if `uv.lock` has drifted from `pyproject.toml` rather than
resolving new versions. After changing a dependency, run `uv lock` and commit
the updated lockfile.

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
uv sync --locked --extra dev
ruff check .
ruff format --check .
mypy                                       # strict mode, over python/ and tests/
cargo clippy --locked --all-targets -- -D warnings
cargo fmt --check
```

Run `pre-commit install` to run all of the above, plus the dependency audits
below, automatically on `git commit`.

## Dependency audits

```
pip-audit    # Python, from the dev extra
cargo audit  # Rust; install once with `cargo install cargo-audit --locked`
```

Both run in CI's `audit` job, so a newly disclosed advisory against a pinned
dependency fails the build.

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

Every pull request against `main` runs seven GitHub Actions jobs
(`.github/workflows/ci.yml`) ahead of review: `lint` (`ruff check`, `ruff
format --check`, strict `mypy`), `rust-lint` (`cargo clippy`, `cargo fmt
--check`), `rust-tests` (`cargo test` and `cargo bench`), `build` (compiles
the extension and smoke-imports `phylo.oxiphylo`), `python-tests` (the full
`pytest` suite, including the `hypothesis` property tests, gated on a
minimum coverage threshold via `pytest-cov`), `docs` (the Sphinx build
above, with warnings as errors), and `audit` (`pip-audit` and `cargo
audit`).

## Reproducibility

Both dependency graphs are locked (`uv.lock`, `Cargo.lock`) and every CI
install passes `--locked`, so a stale lockfile fails the build instead of
silently resolving new versions. The Rust compiler is pinned by
`rust-toolchain.toml`, and CI pins its runner image and `uv` version. Random
draws use seeded `np.random.default_rng`; ruff's `NPY002` rejects the legacy
global `np.random` functions.

## Versioning

The package version lives in one place, `Cargo.toml`'s `[package].version`;
`pyproject.toml` declares it `dynamic` and maturin reads it from there, so
the two can't silently drift out of sync.

## License

MIT — see [LICENSE](LICENSE).

## Development approach

The Rust backend scaffold and the Python test/benchmark harness touched
disjoint files, so two sub-agents built them in parallel — each in its own git
worktree, each opening its own PR. The follow-up work (renaming the extension
to `oxiphylo`, adding Rust tests, wiring CI across both stacks) touched both
halves at once, so a single sequential PR handled it instead. `CLAUDE.md`
records when to prefer each approach.
