# infra/

CI/CD, the agentic workflow, and experiment tracking. Nothing scientific
lives here; everything that decides whether the science is believable does.

Root `CLAUDE.md` holds the repository-wide rules. `DEV.md` documents the
repository settings and CI budget. These are local.

## Hard bounds on what CI runs

These are limits, not defaults, and a PR does not get to raise them:

- **Topological move tests: `n <= 10`.** Exhaustive enumeration is the oracle
  at that size. Larger cases hang the runner and prove nothing more.
- **No performance ranking in GitHub Actions.** Runner hardware varies
  between runs. Benchmarks may execute there; their timings are never
  asserted on and never ranked.
- **Long-running validity tests are release-gated.** An hour-long test is
  worth having and worth not running fifty times a day.

## Experiment tracking

**Aim**, decided: open source and self-hostable, which suits likelihood- and
temperature-curve tracking across many episodes without a hosted account. It
is not yet a dependency: it arrives with the first code that records a run.

Every run records, at minimum, the commit, the `uv.lock` and `Cargo.lock`
hashes, the seed, the dataset identity, the model specification, the move
set, the evaluation budget, and the hardware. A run that cannot be replayed
from its manifest is an anecdote.

## Tickets and the approval flow

- **Priorities.** `high` runs immediately; `medium` runs at the next
  scheduled slot when tokens refresh; `low` runs outside 09:00–17:00
  Princeton time and is the default.
- **Tag every ticket by submodule**, so batches stage against the roadmap
  rather than sprawling across it.
- **`/approve` by a maintainer** opens a pull request, and may do so
  unattended provided the PR implements a plan already posted to the thread.
  A plan that turns out to be flawed gets a revised plan posted in the
  thread, not a silent correction.

## Required checks

Branch protection matches required checks by name, so renaming a CI job
drops its protection silently. Rename and update the protection rule in the
same change.
