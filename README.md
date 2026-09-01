# phylo

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
pytest      # Python: regression tests (tests/regression), a pytest-benchmark
            # suite (tests/benchmarks), and an integration test that the Rust
            # extension imports correctly (tests/test_oxiphylo_bindings.py)
cargo test  # Rust: unit tests for the PyO3 bindings (src/lib.rs)
```

## Linting & type checking

```
pip install ".[dev]"
ruff check .
ruff format --check .
mypy .
```

Python code in this repo is type-hinted; run `mypy` locally before pushing
(it isn't yet a required CI check — see `CLAUDE.md`).

## Continuous integration

Every pull request against `main` runs four GitHub Actions jobs
(`.github/workflows/ci.yml`) ahead of review: `lint` (`ruff check` and
`ruff format --check`), `rust-tests` (`cargo test`), `build` (compiles the
extension and smoke-imports `phylo.oxiphylo`), and `python-tests` (the full
`pytest` suite).

## Development approach

The Rust backend scaffold and the Python test/benchmark harness were
independent pieces of work touching disjoint files, so they were built by
two sub-agents running in parallel — each in an isolated git worktree, each
opening its own PR. The follow-up work (renaming the extension to
`oxiphylo`, adding Rust-side tests, and wiring up CI across both stacks)
touched both halves at once, so it was done sequentially in a single PR
instead of another parallel split — see `CLAUDE.md` for when to prefer one
approach over the other.
