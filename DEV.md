# Developing phylo

How the repository is put together, what CI enforces, and the rules a change
is held to. For getting a checkout running, see [INSTALL.md](INSTALL.md); for
where the science is going, see [ROADMAP.md](ROADMAP.md).

`CLAUDE.md` is the authoritative statement of the conventions summarized
here. Where the two disagree, `CLAUDE.md` wins and this file needs fixing.

## Two kinds of rule

This repository holds two separable things, and keeping them separable is a
deliberate constraint rather than an accident of layout:

- **Infrastructure** — the build, the checks, the release process, the
  agentic workflow. None of it mentions phylogenetics, and all of it would
  transplant to an unrelated scientific project unchanged.
- **Application** — substitution models, likelihoods, tree search, and the
  standards that make claims about them credible. Portable to nothing;
  specific to this science.

Each section below is marked **[infra]** or **[app]**. The point is not
tidiness: an infrastructure section that acquires a phylogenetic assumption
stops being liftable, and an application section that hides in the build
configuration stops being reviewable by someone who knows the science. When
adding a section, decide which it is first.

Sections not marked are about this document or the repository as a whole.

## Layout [app]

| Path | Contents |
| --- | --- |
| `python/phylo/` | the Python package: re-exports, typed stub for the extension, stub CLI |
| `python/phylo/sim/` | data generation and ground-truth retention |
| `python/phylo/likelihood/` | Felsenstein pruning; CPU, CUDA, and Metal dispatch |
| `python/phylo/opt/` | continuous parameter fitting via autodiff (PyTorch) |
| `python/phylo/search/` | move sets, RL agents, temperature schedules |
| `infra/` | CI/CD, agentic workflow, experiment tracking (Aim) |
| `src/lib.rs` | the Rust extension (`oxiphylo`), exposed through PyO3 |
| `benches/` | Criterion benchmarks for the Rust side |
| `tests/` | regression tests, benchmarks, and the Rust-binding integration test |
| `docs/source/` | Sphinx API documentation |
| `docs/tex/` | LaTeX source for the technical document |

Each of those directories carries its own `CLAUDE.md` stating the concerns
local to it — the analytic oracle `sim/` validates against, the NumPy
reference `likelihood/` keeps, the constraint handling in `opt/`, why `n <= 10`
is the right bound in `search/`, and experiment tracking and the ticket policy
in `infra/`. They stack with the root `CLAUDE.md` rather than overriding it,
and they load when a session works with files in that directory. A rule that
binds the whole repository belongs in the root file; these carry only what
applies inside one module.

## The two-language build [infra]

`maturin` builds the Rust extension as part of a normal `pip install .`, so
consumers need no separate build step — but they do need a Rust toolchain.
`pyproject.toml`'s `[tool.maturin]` maps the crate to `phylo.oxiphylo`;
`python/phylo/oxiphylo.pyi` is a hand-written stub that gives `mypy` a view
into the compiled module. Nothing checks the stub against the module, so it
can drift — `python -m mypy.stubtest phylo.oxiphylo` would close that.

## Continuous integration [infra]

Eight jobs (`.github/workflows/ci.yml`) run on every pull request against
`main`:

| Job | What it runs |
| --- | --- |
| `lint` | `ruff check`, `ruff format --check`, strict `mypy` |
| `rust-lint` | `cargo clippy -D warnings`, `cargo fmt --check` |
| `rust-tests` | `cargo test --locked`, then `cargo bench` (informational) |
| `build` | plain `pip install .`, then a smoke import of `phylo.oxiphylo` |
| `python-tests` | the `pytest` suite, gated on a minimum coverage threshold |
| `docs` | the Sphinx build with warnings as errors |
| `technical-doc` | the LaTeX build, failing on undefined references or citations |
| `audit` | `pip-audit` and `cargo audit`, when the locked dependency graph changed |

Three details worth knowing before editing the workflow:

- **The `build` job deliberately uses plain `pip`**, not the lockfile. It
  exercises the path a fresh consumer takes, which no lockfile covers.
- **Job names are load-bearing.** Branch protection matches required checks by
  name, so renaming a job silently drops its protection. Update the
  protection rule in the same change as any rename.
- **The `audit` job skips its own work when nothing it audits has changed.**
  What an audit examines is fixed by `uv.lock` and `Cargo.lock`, so a cache
  marker keyed on their hash records that this exact graph passed, and the
  job exits early on a hit. Building `cargo-audit` costs about four minutes,
  so the binary is cached separately against the version pinned in the
  workflow's `env`. Two consequences: the key carries the ISO week, so an
  unchanged graph is still re-checked weekly against a freshly fetched
  advisory database, and a `schedule:` trigger audits `main` weekly so a
  newly disclosed advisory surfaces without waiting on a lockfile change.
  The marker is written only after both audits pass, and `actions/cache`
  saves it only when the job succeeds, so a failure records nothing.

## Repository settings [infra]

Some of what keeps CI smooth lives in GitHub's settings rather than in this
repository, so it is invisible to `git log` and easy to lose. The intended
configuration:

| Setting | Where | Value |
| --- | --- | --- |
| Automatically delete head branches | Settings → General → Pull Requests | on |
| Allow auto-merge | Settings → General → Pull Requests | on |
| Merge strategy | Settings → General → Pull Requests | exactly one of squash / merge commit enabled |
| Require a pull request before merging | Branch protection, `main` | on |
| Required status checks | Branch protection, `main` | the eight job names above |
| Require branches up to date before merging | Branch protection, `main` | off unless a merge queue is enabled |
| Force pushes and deletions | Branch protection, `main` | blocked |
| Default `GITHUB_TOKEN` permissions | Settings → Actions → General | read-only, elevated per job where needed |
| Allowed actions | Settings → Actions → General | `actions/*` and `dtolnay/rust-toolchain` only |

Four of these carry a rationale worth keeping:

- **Deleting head branches on merge** prevents a merged branch from being
  revived. A stale branch that outlives its merged PR still points at
  pre-merge history, and a PR opened from it silently reverts whatever
  landed in the meantime.
- **One merge strategy, not two.** With several enabled, the shape of the
  history depends on which button the merger happens to click.
- **"Up to date before merging" is off deliberately.** With eight required
  checks it serializes merges and re-runs the full suite for every PR ahead
  in the queue. Enable it only together with a merge queue, which batches
  those runs.
- **Required check names are load-bearing**, as above: renaming a job
  without updating the protection rule drops its protection silently.

## CI budget [infra]

CI exists to catch mistakes, not to measure performance, and the two want
opposite things from a runner.

- **Cap the size of what CI runs.** Topological move tests belong at n ≤ 10,
  where exhaustive enumeration is the oracle. A scaling test at n = 50 buys
  no additional correctness and can run until the job times out.
- **Never rank performance on GitHub runners.** Their hardware varies
  between runs, which is why benchmarks run in CI without asserting on
  their timings. Scaling and comparison runs belong on fixed hardware.
- **Long-running scientific validity tests are release-gated**, not run per
  pull request. A test that takes an hour is worth having and worth not
  running fifty times a day.
- **Superseded runs are cancelled.** The workflow groups by ref, so pushing
  again to a branch cancels the previous run rather than paying for both.

## Reproducibility [infra]

Reproducibility ranks above convenience here, so the environment is pinned end
to end: `uv.lock` and `Cargo.lock` pin both dependency graphs, every CI install
passes `--locked`, `rust-toolchain.toml` pins the compiler, and CI pins its
runner image (`ubuntu-24.04`) and `uv` version. Seed every random draw with
`np.random.default_rng(seed)`; ruff's `NPY002` rejects the legacy global
`np.random` functions.

## Performance work [app]

A hot path goes to the GPU — through PyTorch, Triton, or JAX — when a kernel
plausibly buys 10x or more over the vectorized NumPy reference at the sizes we
actually run, and to the Rust backend otherwise. The 10x figure is a
benchmarked measurement reported in the PR, not an expectation, and every
accelerated kernel keeps its reference implementation as a pinned oracle.
`CLAUDE.md`'s Performance section states the rule in full.

## Testing [app]

Tests exist to establish scientific validity: fixtures come from
component-wise simulation under a known generative model, expected values come
from an analytic or brute-force source, and tests check the invariants the
mathematics guarantees. Shape-only and runs-without-raising assertions are not
tests. `CLAUDE.md`'s Testing section states the rule in full, and the current
scaffolding suite does not yet meet it — see its Known gaps.

## The technical document [app]

`docs/tex/` holds the LaTeX source for the technical PDF: scientific
background, model definitions, equations, and algorithm statements, plus the
captions for the figures and tables the QA suite emits. It is versioned with
the code, and a PR that changes a model, an equation, an algorithm, or a
figure updates it in the same PR.

## Adding a dependency [infra]

1. Ask first. New dependencies — Python packages, Rust crates, GitHub Actions,
   or other external tools — need explicit permission before they are added,
   and must be open source under an OSI-approved license.
2. Check adoption. Flag anything below roughly 1,000 GitHub stars (or a
   comparable bar on its ecosystem's usual metric) so the decision is
   deliberate.
3. Lock it. Run `uv lock` (Python) or let Cargo update `Cargo.lock` (Rust) and
   commit the result in the same PR — CI's `--locked` installs fail otherwise.
4. Justify it in the PR description.

## Versioning [infra]

The version lives in exactly one place, `Cargo.toml`'s `[package].version`.
`pyproject.toml` declares it `dynamic` and maturin reads it from the crate, so
the two cannot drift. Never hardcode a second version number.

## The changelog [infra]

`CHANGELOG.md` is assembled, not edited. Each change adds a file to
`changelog.d/` named `<id>.<category>.md` — the pull-request number and one of
the Keep a Changelog headings — containing the entry text. Two pull requests
never touch the same file, so the changelog cannot conflict on merge, which a
shared file did three times in one week.

```
echo "What changed, in a sentence." > changelog.d/42.added.md
python -m infra.changelog --check      # names and categories
python -m infra.changelog --assemble   # at release: fold in, delete fragments
```

CI validates every fragment name, and requires a fragment on each pull request
unless it carries the `skip-changelog` label.

## Tickets and priorities [infra]

Issues are filed from `.github/ISSUE_TEMPLATE/task.yml`, which asks for the
outcome, why it matters, the submodule, and how the work will be validated.
Labels are defined in `.github/labels.yml` and applied by the **Labels**
workflow, so the taxonomy follows the file rather than whatever accumulated in
the web interface.

| Label | Schedules |
| --- | --- |
| `priority:high` | Runs immediately |
| `priority:medium` | Runs at the next scheduled slot, when tokens refresh |
| `priority:low` | Runs outside 09:00–17:00 Princeton time. Applied by default |
| `module:*` | Tags the submodule, so tickets batch against the roadmap |
| `approved` | A maintainer has approved the posted plan |

`infra/CLAUDE.md` carries the approval policy: `/approve` opens a pull request
implementing a plan already posted to the thread, and a flawed plan gets a
revised plan in-thread rather than a silent correction. The workflow that
automates it is not built — it needs an action the allowed list does not yet
permit.

## Definition of done

`CLAUDE.md`'s Definition of Done is the checklist, and restating it here
would only give it somewhere to go stale. One addition belongs to this file:
a PR that changes whether something exists also updates its row in
[STATUS.md](STATUS.md). That file stands in for a project board, so it is
only worth having while it is accurate.

## Development approach

The Rust backend scaffold and the Python test/benchmark harness touched
disjoint files, so two sub-agents built them in parallel — each in its own git
worktree, each opening its own PR. The follow-up work (renaming the extension
to `oxiphylo`, adding Rust tests, wiring CI across both stacks) touched both
halves at once, so a single sequential PR handled it instead. `CLAUDE.md`
records when to prefer each approach.
