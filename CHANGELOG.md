# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

New entries are managed as [towncrier](https://towncrier.readthedocs.io)
fragments under `changelog.d/` (see `changelog.d/README.md`) and merged into
this file at release time; the `[Unreleased]` section below predates that
convention and is retained as history.

<!-- towncrier release notes start -->

## [0.1.0] - 2026-09-02

### Added

- `k`-state Jukes–Cantor sequence simulator in `phylo.sim`: generates an
  alignment and the ancestral tree in Newick from a typed
  `simulation_params.yaml`, and retains the parameters that generated them.
  Simulated substitution frequencies are validated against the closed-form JC
  transition probabilities within a yaml-declared Monte Carlo tolerance across
  several site and taxa sizes. Promotes `numpy` and `pyyaml` to core
  dependencies. (#55)
- Added `phylo.sim.newick`: topology counting (`count_topologies`), Newick string validation (`validate_newick`), and state-labelled Newick serialization (`to_newick`), now the package's single source of Newick functionality. (#60)
- Added `phylo.qa`, quality-assurance figure scripts for the technical document, starting with `phylo.qa.sim_tree` (renders the assumed simulation tree with branch lengths). `infra/build_technical_doc.sh` regenerates these figures and builds `docs/draft.pdf`. (#61)
- Vectorized NumPy Felsenstein pruning in `phylo.likelihood`, computing
  `ln L(alignment | tau, Q, t, pi)` under the k-state Jukes-Cantor model with
  per-node rescaling accumulated in log space. Ships with an independent
  brute-force marginalizer used only as the test oracle at `n <= 6` taxa.
  Validated against brute-force marginalization to machine precision,
  rescaled/unrescaled agreement, the pulley principle (root-position
  invariance), and scoring the generating topology above random wrong
  topologies on simulated data. This is the reference every future backend
  (Rust, PyTorch, CUDA, Metal) is pinned against. (#62)
- Added `phylo.qa.sim_example` and `phylo.qa.sim_problem_sizes`: a worked
  4-taxon simulation example (Newick topology and aligned sequences) and a
  cross-fixture table of problem-size parameters (taxa, sites, seed,
  tolerance), read directly from the `simulation_params.yaml` fixtures. Wired
  into `infra/build_technical_doc.sh` and `docs/tex/main.tex`. (#67)
- Differentiable PyTorch Felsenstein pruning (`phylo.likelihood.pruning_torch`),
  taking branch lengths as a `torch.float64` CPU tensor separate from the
  topology so `torch.autograd` differentiates through them. Validated against
  the NumPy oracle and brute-force marginalization to `atol=1e-9`, against
  `torch.autograd.gradcheck` and central finite differences of the NumPy
  likelihood to `atol=1e-6`, and rescaled/unrescaled agreement. A general
  `rate_matrix` path (`torch.matrix_exp`) is exercised by a benchmark fitting a
  Jukes-Cantor rate matrix Q, alongside a forward-pass benchmark against the
  NumPy reference. (#70)
- Rust CPU Felsenstein pruning backend (`oxiphylo.pruning_log_likelihood`,
  exposed via `phylo.likelihood.pruning_rust`), implementing the same
  recursion as the NumPy oracle in `src/pruning.rs` and exposed through PyO3.
  Validated against the NumPy oracle and independent brute-force
  marginalization at `n <= 6` taxa, and against the NumPy oracle at realistic
  (taxa, site) sizes to `abs_tol=1e-9`. Ships a `criterion` benchmark
  (`benches/oxiphylo_bench.rs`) and a paired `tests/regression/test_pruning_rust.py`
  / `tests/benchmarks/test_pruning_rust_bench.py` module, reporting Rust vs.
  NumPy timings at 4- and 8-taxon, 200,000-site fixtures. (#77)
- NNI and SPR neighbourhood generators over unrooted binary topologies
  (`phylo.search.topology`), behind one `Topology -> Iterator[Topology]`
  interface. Validated exhaustively against `2 * (n - 3)` (NNI) and
  `2 * (n - 3) * (2 * n - 7)` (SPR) at `n = 5..8` -- every one of the
  `count_topologies(n - 1)` distinct topologies, cross-checked for neighbour
  validity, symmetry, and NNI-in-SPR containment (`n = 8` gated to
  `pytest -m release`, ~2.5 minutes). `phylo.sim.newick` gains
  `validate_unrooted_newick` for the trifurcating-root convention this reuses.
  The random-walk connectivity test is deferred to issue #73's canonical
  Newick key. (#79)
- Added a Release issue template (`.github/ISSUE_TEMPLATE/release.yml`) that
  drives the repository-consolidation audit ahead of a release, and
  `infra/release.sh`, a local release gate running every per-PR CI check plus
  the release-gated `pytest` tests, `sphinx-build -W`, and the technical
  document build. `DEV.md` documents the release procedure, including the
  version-bump and tag/publish steps. (#90)

### Changed

- `DEV.md` states the `tests/` layout convention: organized by kind
  (`regression/`, `benchmarks/`) at the top level and by subject within it, with
  rules for benchmark/regression pairing, fixture placement, and when a kind
  splits into submodule subdirectories. (#45)
- The rendered technical document (`docs/draft.pdf`) is now committed to the
  repository instead of being a gitignored build artifact. CI's
  `technical-doc` job fails a PR whose rebuilt PDF differs from the committed
  one, catching a `docs/tex/` or QA-figure change that wasn't regenerated. (#71)
- PR template gained a "Follow-up / Deferred Work" section for TODOs left to a tracking issue. (#84)
- `docs/tex/main.tex` now states its intended reader (a developer with
  baseline scientific/performance-computing background but no phylogenetics
  expertise) and the formatting contract that follows from it: streamlined
  main text, standard non-phylo-specific background (e.g. NNI, SPR) moved to
  a new appendix and cited from the point of use. `CLAUDE.md` records the
  same contract for anyone editing the document. (#85)
- PR template's Benchmark section gained a second table for scientific/tolerance regression tests, so contributors report the realized value alongside the reference and tolerance it was checked against. (#88)
- Simplified the Release issue template (`.github/ISSUE_TEMPLATE/release.yml`):
  the consistency-audit field is no longer required — the ticket's job is to
  trigger the consolidation audit and surface follow-up tickets, not to gate
  submission on having written them out — and the `infra/release.sh` checkbox
  is dropped. That check is already enforced by the documented release
  procedure (`DEV.md`'s "Release" section): the gate is run, and only then is
  the version bumped and the tag cut. (#94)

### Fixed

- Embedded TrueType (not Type 3) fonts in QA figures, fixing `docs/draft.pdf`'s failure to render in GitHub's blob viewer. (#76)
- Fixed the Release issue template (`.github/ISSUE_TEMPLATE/release.yml`):
  `roadmap-progress`, `consistency-audit`, and `follow-up-tickets` moved their
  guidance from `description:` (static gray helper text below the box) into
  `value:` (the box's own prefilled, editable content), so filers answer the
  ask instead of retyping it. (#98)


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
