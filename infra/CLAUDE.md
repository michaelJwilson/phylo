# infra/

CI/CD, the agentic workflow, and experiment tracking. No scientific application
references live here; everything that efficiently developed the science and supports
proof that it is valid does.

Root `CLAUDE.md` holds the repository-wide rules. `DEV.md` holds the CI
budget, the repository settings, and the eight CI jobs — including the two
that bind hardest here: discrete problem sizes, e.g. trees, are capped at `n <= 10`,
so tests complete.

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
