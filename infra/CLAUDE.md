# infra/

CI/CD, the agentic workflow, and experiment tracking. Nothing scientific
lives here; everything that decides whether the science is believable does.

Root `CLAUDE.md` holds the repository-wide rules. `DEV.md` holds the CI
budget, the repository settings, and the eight CI jobs — including the two
that bind hardest here: topological tests are capped at `n <= 10`, and
performance is never ranked on GitHub runners. These are local.

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
