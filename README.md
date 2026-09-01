# phylo

[![CI](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`phylo` is a high-performance scientific Python package with a Rust-accelerated
backend (`phylo.oxiphylo`, via [PyO3](https://pyo3.rs)/[maturin](https://www.maturin.rs)).

Its goal is to solve the large parsimony problem — the search over
phylogenetic tree topologies — with reinforcement learning, scoring candidate
trees by the Felsenstein likelihood under a substitution model. That rests on
fast simulation, fast likelihood evaluation, and automatic differentiation;
[ROADMAP.md](ROADMAP.md) sets out the plan and the milestones.

The repository today is scaffolding. Every function in it is a placeholder,
and the science described in the roadmap is not implemented yet.

## Quick start

```
uv sync --locked --all-extras
source .venv/bin/activate
pytest
```

[INSTALL.md](INSTALL.md) covers the full workflow: prerequisites, building the
Rust extension, running both test suites, the checks CI enforces, dependency
audits, and building the docs.

## Documentation

| Document | Contents |
| --- | --- |
| [INSTALL.md](INSTALL.md) | Installing, building, running the tests, and working locally |
| [DEV.md](DEV.md) | Repository layout, CI jobs, conventions, and how a change is reviewed |
| [ROADMAP.md](ROADMAP.md) | The long-term scientific goal and its milestones |
| [CHANGELOG.md](CHANGELOG.md) | What has landed so far |
| `CLAUDE.md` | The authoritative conventions, including performance and testing policy |
| `docs/source/` | Sphinx API documentation, built from the docstrings |
| `docs/tex/` | LaTeX source for the technical document: background, equations, algorithms |

## License

MIT — see [LICENSE](LICENSE).
