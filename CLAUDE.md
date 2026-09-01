# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

`phylo` is a high-performance scientific Python repository. Correctness and
reproducibility of numerical/scientific results take priority over
convenience.

## Environment

Use `uv` for environment and dependency management (Python 3.12):

```
uv sync --locked --all-extras
source .venv/bin/activate
```

`--locked` fails if `uv.lock` has drifted from `pyproject.toml` instead of
resolving something new. After changing a dependency, run `uv lock` and commit
the updated `uv.lock` in the same PR.

## Conventions

- Prefer vectorized (NumPy/array-based) implementations over Python loops on
  hot paths; justify any deviation with a comment. See Performance below for
  which accelerator a hot path graduates to.
- Any change affecting numerical output must include or update a test that
  pins expected values (or tolerances). See Testing below for what counts as
  a test here.
- Keep dependencies minimal — new dependencies should be justified in the PR
  description.
- Do not silently change default parameters of scientific algorithms.
- Use type hints on all Python function signatures (see Tooling below).
- Any PR that changes behavior, conventions, or the dev/CI setup must update
  `README.md` and/or `CLAUDE.md` in the same PR, so the docs never drift
  from what's actually in the repo. If the change is user-visible, add a
  `CHANGELOG.md` entry under `[Unreleased]` too.
- The package version lives in exactly one place, `Cargo.toml`'s
  `[package].version` (`pyproject.toml` reads it dynamically via maturin —
  see `README.md`'s Versioning section). Never hardcode a second version
  number anywhere.

## Performance

Hot paths get the fastest implementation that keeps the numbers correct and
the code reviewable. Pick the target in this order:

- **GPU, where the arithmetic earns it.** When a hot path is data-parallel
  and a GPU kernel plausibly buys 10x or more over the vectorized NumPy
  reference at the problem sizes we actually run, put it on the GPU through
  the standard Python ecosystem — PyTorch, Triton, or JAX — rather than
  hand-written CUDA. Those frameworks already carry autodiff, batching, and
  device portability, all of which a bespoke kernel would have to
  reimplement and maintain.
- **Otherwise the Rust backend.** A hot path that stays on the CPU — control
  flow, tree traversal, irregular memory access, small problem sizes — moves
  into `oxiphylo` (Rust, via PyO3), not into hand-tuned Python.
- **10x is a measurement, not a hunch.** Benchmark the candidate against the
  NumPy reference at realistic sizes before committing to a GPU port, and
  report both numbers in the PR description. A speedup that only appears at
  sizes we never run does not justify the port.
- **Every accelerated kernel keeps its reference.** The NumPy (or pure-Python)
  implementation stays as the oracle, and a regression test pins the
  accelerated output against it within an explicit tolerance. A kernel that
  is fast and wrong is a regression, not an optimization.
- **Benchmark what you accelerate.** New or materially changed hot functions
  get a `pytest-benchmark` test (Python/GPU) or a `criterion` benchmark in
  `benches/` (Rust), per the Definition of done below.

PyTorch, Triton, and JAX are not dependencies of this project today. This
section records where they belong when the work arrives; adding one still
needs explicit permission first, per Dependencies & external tools below.

## Testing

Tests establish scientific validity. A test that cannot fail for a
scientific reason does not belong in the suite.

- **Simulate component-wise.** Build fixtures by simulating from a known
  generative model — rate matrix, branch lengths, root distribution, tree —
  with an explicitly seeded generator, then test each component against the
  value that model implies. Simulating the whole pipeline and checking only
  the end-to-end output hides which component broke.
- **Pin numbers against an independent source.** Expected values come from
  an analytic result, a brute-force computation, or a second implementation
  — not from recording what the code printed on the day it was written.
  State the tolerance explicitly.
- **Check the invariants the mathematics guarantees.** Rows of a transition
  matrix sum to one; a reversible model satisfies detailed balance
  (`π_i q_ij = π_j q_ji`); pruning-algorithm likelihoods match brute-force
  marginalization on small trees; autodiff gradients match finite
  differences; likelihood increases monotonically under optimization.
- **Keep the QA framework current.** The suite emits scientific-style plots
  and tables (parameter recovery, likelihood surfaces, convergence,
  timings). Their captions live in the LaTeX technical document (see
  Technical document below) and are updated in the same PR that changes the
  figure — a plot whose caption describes an older experiment is worse than
  no plot.
- **Never write a test that obfuscates validity.** Asserting only that an
  array has a given shape or dtype, that a call returns without raising, or
  that a placeholder prints something is coverage theatre, not testing. If
  the science is not implemented yet, leave the test unwritten and record
  the gap under Known gaps instead of banking coverage against a stub.

## Technical document

`docs/tex/` holds the LaTeX source for the project's technical PDF: the
scientific background, model definitions, equations, and algorithm
statements behind the code. Treat it as part of the code, not an appendix
to it — a PR that adds or changes a model, an equation, an algorithm, or a
QA figure updates the document in the same PR.

## Reference sources

Cite these texts in the technical document wherever they cover the
background. Where an algorithm we implement appears in one of them, follow
its formulation and notation, and state explicitly where and why we
deviate.

- Hwu, Kirk & El Hajj, *Programming Massively Parallel Processors* — GPU
  kernels, memory hierarchy, occupancy, parallel reduction and scan.
- MacKay, *Information Theory, Inference, and Learning Algorithms* —
  inference, message passing, Monte Carlo, model comparison.
- Goodfellow, Bengio & Courville, *Deep Learning*, and Prince,
  *Understanding Deep Learning* — architectures, optimization, automatic
  differentiation.
- Sutton & Barto, *Reinforcement Learning: An Introduction* — MDPs, value
  and policy methods, exploration, search.
- Felsenstein, *Inferring Phylogenies* — substitution models, the pruning
  algorithm, tree search, parsimony and likelihood criteria.

## Writing style

Applies to docstrings, comments, commit messages, PR descriptions, and
README/CLAUDE.md prose. Rooted in Strunk & White's *Elements of Style*,
trimmed to what matters for technical writing, plus habits drawn from
evidence-driven journalism (e.g. the New York Times) for backing claims:

**Elements of Style**
- Omit needless words.
- Use active voice.
- Prefer definite, specific, concrete language over vague generalities.
- State things in positive form.
- Express parallel/coordinate ideas in matching grammatical form.
- Keep related words together.
- Favor nouns and strong verbs; don't lean on adjectives/adverbs instead.
- Avoid strings of loose, run-on clauses.
- Do not overstate.
- Avoid weak qualifiers ("very," "rather," "pretty," "little").
- Do not over-explain — trust the reader.
- Write plainly; skip inflated vocabulary and jargon for its own sake.
- Revise before committing — first drafts are rarely final.
- Keep opinion out of factual/technical writing unless explicitly asked for.

**Evidence & clarity (from evidence-driven journalism)**
- Lead with the most important fact or conclusion first.
- State early why a change matters.
- Back every claim with evidence — test output, benchmark numbers, a
  reproduction — not bare assertion (e.g. "3 passed, 100% coverage," not
  "should work now").
- Prefer precise facts/numbers over vague intensifiers ("40% faster," not
  "much faster").
- Keep a neutral, measured tone — no hype or marketing language.
- Favor short paragraphs and sentences for scannability.
- Cut anything that doesn't advance the point.
- Apply one consistent style throughout (naming, terminology, formatting)
  — enforced here via ruff/mypy/clippy/fmt rather than left to habit.

(Dropped from the source material as not relevant to technical/code
writing: fine-grained punctuation mechanics like the possessive-'s and
comma-splice rules — general English grammar, not particular to writing
about code; "place the emphatic word at the end" — a rhetorical device for
narrative prose, superseded here by leading with the key fact instead;
quoting sources — there are no interview subjects in code; and writing
for auditory rhythm — code docs optimize for scanning, not being read
aloud.)

## Definition of done for new or changed functionality

Beyond "it works," a PR that adds or changes package behavior (not a
docs/CI-only change) should leave the repo in this state for the code it
touches — use judgment on what's proportionate to the PR's size, but don't
skip an item because it's inconvenient:

- **Regression test**: pins expected output per the Conventions above, and
  tests scientific validity per Testing above — shape-only or
  runs-without-raising assertions do not satisfy this item.
- **Benchmark**: any new or materially changed hot function gets a
  `pytest-benchmark` test (Python) or a `criterion` benchmark in `benches/`
  (Rust), and the resulting numbers get reported in the PR description as
  the baseline for future comparison — even though CI doesn't hard-gate on
  them (see Tooling: comparisons are local-only, not CI-blocking, due to
  GitHub-hosted runner hardware variance).
- **Coverage**: doesn't drop the repo below the CI coverage gate
  (`--cov-fail-under` in the `python-tests` job). Raise the gate as
  coverage improves over time; never lower it just to make a PR pass —
  write the missing test instead.
- **Lint/type/format**: `ruff check`, `ruff format --check`, `mypy`
  (Python) and `cargo clippy`, `cargo fmt --check` (Rust) all pass locally
  before pushing — all four are required CI checks already, this just
  means not relying on CI (or a reviewer) to catch it first.
- **CI coverage of the change itself**: if a PR introduces a new language,
  build target, or category of code that none of the existing CI jobs
  would exercise, add or extend a CI job for it in the same PR — don't
  leave a new category of code untested "for a follow-up."
- **Docs**: see the Conventions bullet above (README/CLAUDE.md/CHANGELOG),
  plus the technical document when the PR changes a model, equation,
  algorithm, or QA figure caption (see Technical document above).
- **Dependency hygiene**: any new dependency follows the Dependencies &
  external tools rules below.

## Tooling

- Lint/format Python with `ruff check .` and `ruff format --check .`;
  type-check with `mypy`, which runs in `strict` mode over both `python/`
  and `tests/`. All three are enforced in CI (`.github/workflows/ci.yml`'s
  `lint` job) — ruff's `ANN` (annotation-presence) rules stay disabled in
  `pyproject.toml` because `mypy --strict` already rejects an unannotated
  signature.
- Audit dependencies with `pip-audit` (Python) and `cargo audit` (Rust);
  both run in CI's `audit` job and as pre-commit hooks. `cargo audit` is not
  part of the Rust toolchain — install it with
  `cargo install cargo-audit --locked`.
- Lint/format Rust with `cargo clippy --all-targets -- -D warnings` and
  `cargo fmt --check`; both are enforced in CI (`rust-lint` job).
- Optionally install `pre-commit` (`pip install ".[dev]"` includes it,
  then `pre-commit install`) to run all of the above automatically on
  `git commit`, catching issues before they reach CI.
- `pytest-benchmark`'s baseline-comparison flags (`--benchmark-autosave`,
  `--benchmark-compare`, `--benchmark-compare-fail`) are deliberately not
  part of the shared pytest config or CI: GitHub-hosted runners vary in
  hardware between runs, so a fixed-baseline comparison there would be
  flaky rather than a reliable regression signal. Use them locally instead,
  e.g. `pytest tests/benchmarks --benchmark-autosave` once to establish a
  baseline, then `--benchmark-compare=0001 --benchmark-compare-fail=mean:5%`
  on later runs. `cargo bench` (Criterion) runs in CI unconditionally
  (informational only, nothing is asserted against its timings, so it
  can't flake); use `cargo bench` locally with Criterion's own
  `--baseline`/`--save-baseline` for local regression comparison.
- API docs build with Sphinx (`docs/source/`, NumPy-style docstrings via
  `napoleon`); CI runs `sphinx-build -W` (warnings as errors) in the `docs`
  job. Write docstrings knowing they're rendered, not just read in-editor.

## Reproducibility

Reproducibility is the project's stated priority, so the environment is
pinned end to end. Keep it that way:

- **Both dependency graphs are locked.** `uv.lock` pins Python, `Cargo.lock`
  pins Rust. Every install in CI passes `--locked`, which fails on a stale
  lockfile rather than resolving something new. Regenerate with `uv lock` /
  `cargo update` deliberately, and commit the result in the same PR.
- **The toolchains are pinned.** `rust-toolchain.toml` fixes the Rust
  compiler; CI pins the runner image (`ubuntu-24.04`, not `ubuntu-latest`)
  and the `uv` version.
- **Seed every random draw explicitly**, using `np.random.default_rng(seed)`.
  Never use the legacy global `np.random.*` functions — ruff's `NPY002`
  rejects them.
- The `build` CI job deliberately installs with plain `pip` instead of the
  lockfile: it checks the path a fresh consumer takes, which no lockfile
  protects.

## Known gaps

Current as of the initial scaffolding. Don't assume any of this exists; close
a gap deliberately, in its own PR, rather than assuming a past PR covered it.

- **No real science yet.** Every function in the repo is a placeholder
  (`double`, `pairwise_distance`). The coverage gate and benchmarks are
  calibrated against ~5 statements of trivial Python, so treat the 100%
  coverage figure as a smoke test, not evidence of a tested codebase.
- **The current suite violates the Testing rules above.** The benchmark test
  asserts only an output shape, and the CLI test asserts only that a
  placeholder printed something. They date from the scaffolding and are
  exactly the pattern Testing forbids. Replace them with validity tests as
  the science lands; do not copy them as a template.
- **No simulation or QA framework yet.** Nothing generates the
  component-wise simulated fixtures Testing requires, and no test emits the
  plots or tables whose captions the technical document is meant to carry.
- **The Rust backend accelerates nothing.** The only numerical function lives
  in `tests/`, in pure NumPy. Nothing yet demonstrates the intended pattern: a
  kernel in Rust, called from Python, benchmarked against a NumPy reference,
  with values pinned. Building that is the highest-value next step — it
  exercises every part of this framework at once and gives contributors a
  template.
- **`python/phylo/` has no module structure.** It holds a re-export and a stub
  CLI. There is no `core.py`-equivalent, so there is no established home or
  naming pattern for real algorithms.
- **Nothing detects performance regressions.** Benchmarks run in CI but assert
  nothing (deliberately — runner hardware varies), and the
  report-numbers-in-the-PR policy relies on human attention, not a mechanism.
- **One platform, one Python version.** CI tests `ubuntu-latest` on 3.12 only,
  while `requires-python` claims `>=3.12.2` — 3.13+ and macOS/Windows are
  untested.
- **No distributable artifact.** There is no wheel-building or publishing
  workflow, so installing requires a Rust toolchain.
- **`oxiphylo.pyi` can drift.** The stub is hand-written and nothing checks it
  against the compiled module; `python -m mypy.stubtest phylo.oxiphylo` would.
- **CI job names are load-bearing.** Branch protection matches required checks
  by job name, so renaming a job silently drops its protection. Update the
  branch-protection rule in the same change as any rename.

## Working with sub-agents

- When a task naturally splits into pieces that touch disjoint files (e.g. a
  Rust extension scaffold vs. a Python test harness), prefer parallel
  sub-agents, each in its own isolated git worktree, each opening its own
  PR. This keeps PRs small and independently reviewable and avoids merge
  conflicts between the pieces.
- When a task is coupled — it touches files another piece already owns, or
  its output depends on decisions made there (e.g. renaming the Rust
  extension, then wiring CI that has to know about both the Rust and Python
  halves) — do it sequentially in a single thread instead. Splitting coupled
  work across agents mostly adds cost (each agent re-derives context from
  scratch) without buying real parallelism, since the pieces still have to
  be reconciled by hand.

## Dependencies & external tools

- Any new dependency (Python package, Rust crate, GitHub Action, or other
  external tool) must be open source under an OSI-approved license. Do not
  add anything with a proprietary, unclear, or non-OSS license.
- Do not add a new external dependency or tool without the user's explicit
  permission first — ask before adding, don't add and explain afterward.
- When proposing a new dependency, check its popularity (GitHub stars,
  PyPI/crates.io download counts, or an equivalent adoption metric for its
  ecosystem) and flag it explicitly if it falls short of roughly 1,000
  GitHub stars (or a comparably low bar on its ecosystem's usual metric) —
  let the user decide whether a less-established tool is still the right
  call.
