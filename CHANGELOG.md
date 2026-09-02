# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

New entries are managed as [towncrier](https://towncrier.readthedocs.io)
fragments under `changelog.d/` (see `changelog.d/README.md`) and merged into
this file at release time; the `[Unreleased]` section below predates that
convention and is retained as history.

<!-- towncrier release notes start -->

## [Unreleased]

### Added

- Changelog Automation: Adopted [towncrier](https://towncrier.readthedocs.io) to manage `CHANGELOG.md` via fragments in `changelog.d/`, restoring the no-merge-conflict, CI-enforced workflow of the bespoke system removed below — as a maintained dependency instead of custom infra code.
- Project Scaffolding: Initialized uv-based Python 3.12 environment and Rust backend via maturin/PyO3 (phylo.oxiphylo).
- Module Architecture: Established core package skeleton (sim, likelihood, opt, search, infra) enforcing a strict separation between infrastructure and domain-specific application logic.
- Documentation Suite: Deployed Sphinx API docs, a LaTeX technical document for scientific foundations, and strategic planning documents (ROADMAP.md, STATUS.md, DEV.md).
- CI/CD Pipeline: Implemented GitHub Actions for Python/Rust linting, testing, documentation building, and dependency auditing using strictly locked environments (uv.lock, Cargo.lock).

### Changed

- Scientific Modeling: Formalized the Canonical Newick form and k-state Jukes–Cantor transition probabilities within the technical documentation.
- Strategic Roadmap: Defined strict engineering requirements (problem scale n=10−1000, RF ≤0.05, sub-second gradients) and partitioned development into six distinct workstreams.
- Framework Selection: Designated PyTorch as the primary autodiff engine and Aim for experiment tracking.
- Code Quality: Enforced mypy strict mode across all modules, required explicit np.random.default_rng for benchmarking, and applied standard linting rules to test suites.
- CI Optimization: Streamlined CI by caching uv/Cargo environments, auditing only modified dependency graphs, and auto-canceling superseded branch runs.

### Fixed

- Resolved dependency resolution failures in CI linting jobs and pinned cargo-audit to prevent floating resolve breakages.

### Removed

- Deprecated automated changelog fragments (changelog.d/) and associated infra/changelog.py script in favor of a standard flat file. (Superseded: this file's fragment-based workflow is restored via towncrier, a maintained dependency, rather than the bespoke infra removed here — see the towncrier adoption entry above.)
- Removed unused pytest-xdist dependency and legacy infra/ scaffolding modules.

### Security

- Raised pytest dependency to >=9.0.3 to patch vulnerability PYSEC-2026-1845.
