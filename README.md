# phylo

[![CI](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml/badge.svg)](https://github.com/michaelJwilson/phylo/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

`phylo` is a high-performance scientific Python package with a Rust-accelerated
backend (`phylo.oxiphylo`, via [PyO3](https://pyo3.rs)/[maturin](https://www.maturin.rs))
for modern phylogenetic inference. 

Its goal is to solve the large parsimony problem — the search over
phylogenetic tree topologies — with reinforcement learning, scoring candidate
trees by the Felsenstein likelihood under a substitution model. 

[ROADMAP.md](ROADMAP.md) sets out the plan and the milestones.

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

| Document | Contents | Axis |
| --- | --- | --- |
| [INSTALL.md](INSTALL.md) | Installing, building, running the tests, and working locally | infrastructure |
| [DEV.md](DEV.md) | Repository layout, CI jobs, conventions, and how a change is reviewed | both, marked per section |
| [ROADMAP.md](ROADMAP.md) | The long-term scientific goal, requirements, and milestones | application |
| [CHANGELOG.md](CHANGELOG.md) | What has landed so far | infrastructure |
| `CLAUDE.md` | The authoritative conventions, including performance and testing policy | both |
| `docs/source/` | Sphinx API documentation, built from the docstrings | infrastructure |
| `docs/tex/` | LaTeX source for the technical document: background, equations, algorithms | application |

## License

MIT — see [LICENSE](LICENSE).
