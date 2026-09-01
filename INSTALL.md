# Installing and running phylo locally

Everything needed to get a working checkout: the environment, the build, the
test suites, and the checks CI will run against your branch. For how the
project is developed — layout, CI, conventions — see [DEV.md](DEV.md).

## Prerequisites

| Tool | Version | Notes |
| --- | --- | --- |
| Python | >= 3.12.2 | `requires-python` in `pyproject.toml` |
| Rust | 1.94.1 | pinned by `rust-toolchain.toml`; `rustup` installs it automatically |
| [uv](https://docs.astral.sh/uv/) | 0.8.17 | the version CI pins |

The package compiles a Rust extension on install, so a Rust toolchain is
required even for a Python-only workflow.

## Environment

```
uv sync --locked --all-extras
source .venv/bin/activate
```

`--locked` fails if `uv.lock` has drifted from `pyproject.toml` rather than
resolving new versions, so the environment matches CI's exactly. After
changing a dependency, run `uv lock` and commit the updated lockfile in the
same PR.

The extras are `dev` (ruff, mypy, pre-commit, pip-audit), `test` (pytest and
plugins, NumPy), and `docs` (Sphinx). `--all-extras` installs all three; sync
a single one with `uv sync --locked --extra test`.

## Building

`maturin` is the PEP 517 build backend, so a normal install compiles the Rust
extension:

```
pip install .
```

This makes `phylo.oxiphylo` (currently one example binding, `double`)
importable from Python. Reinstall after editing anything under `src/` — the
compiled module does not rebuild itself.

## Running the tests

```
pytest      # Python: regression tests (tests/regression), a pytest-benchmark
            # suite (tests/benchmarks), and an integration test that the Rust
            # extension imports correctly (tests/test_oxiphylo_bindings.py)
cargo test  # Rust: unit tests for the PyO3 bindings (src/lib.rs)
cargo bench # Rust: Criterion benchmarks (benches/)
```

`pytest` reads its configuration from `pyproject.toml`. To reproduce the CI
gate, including coverage:

```
pytest --cov=phylo --cov-report=term-missing --cov-fail-under=90
```

## Checks CI will run

Run these before pushing; all of them are required checks.

```
ruff check .
ruff format --check .
mypy                                       # strict, over python/ and tests/
cargo clippy --locked --all-targets -- -D warnings
cargo fmt --check
```

`pre-commit install` runs the same checks, plus the dependency audits below,
on every `git commit`.

## Dependency audits

```
pip-audit    # Python, from the dev extra
cargo audit  # Rust; install once with `cargo install cargo-audit --locked`
```

Both run in CI's `audit` job, so a newly disclosed advisory against a pinned
dependency fails the build.

## Building the documentation

API documentation, from the NumPy-style docstrings:

```
sphinx-build -b html docs/source docs/_build/html -W
```

Open `docs/_build/html/index.html`. The `-W` flag turns warnings into errors,
matching CI, so a broken docstring or cross-reference fails locally rather
than in review.

The technical document — the scientific background, equations, and algorithms
— is LaTeX under `docs/tex/`, built with `latexmk -pdf` and described in
[DEV.md](DEV.md).

## Benchmarking locally

CI runs the benchmarks but asserts nothing against their timings, because
GitHub-hosted runner hardware varies between runs. Compare against a baseline
locally instead:

```
pytest tests/benchmarks --benchmark-autosave            # establish a baseline
pytest tests/benchmarks --benchmark-compare=0001 \
                        --benchmark-compare-fail=mean:5%

cargo bench -- --save-baseline main                      # Criterion equivalent
cargo bench -- --baseline main
```
