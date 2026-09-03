# infra/

CI/CD, the agentic workflow, and experiment tracking. No scientific application
references live here; everything that efficiently developed the science and supports
proof that it is valid does.

`select_tests.py` decides which tests a pull request needs and what to measure
coverage over, from the files it changed. It reads the import graph rather than
a list of dependents, and answers "everything" for any change it cannot
attribute to one module — a lockfile, a shared fixture, this directory. A
selection that guesses narrowly is a test that silently did not run, so the
unsafe answer is the one that looks like a saving.

Root `CLAUDE.md` holds the repository-wide rules, and its **Writing Style**
section binds this file too — and every docstring, comment and commit message
in this module. It is referenced here, never restated. What follows is local. `DEV.md` holds the CI
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
- **Once a branch is created for an approved plan**, the first thing posted
  is a single issue comment naming the branch (and, once opened, the PR
  number) before any further commit is pushed. A session that fails, is
  interrupted, or is deferred mid-implementation then leaves a ticket that
  already points at the in-flight branch, instead of one requiring a search
  across open branches and PRs to find it.
- **A plan is 2–5 steps**, or more where the work needs them and the plan
  says why, each stating how it will be validated — the analytic result,
  brute-force computation or enumeration it is checked against, not "tests
  pass". It ends with an `Open Questions` section carrying every question on
  the desired behaviour, so a reviewer finds them in one place; a plan with
  none says so under that heading rather than omitting it. This is the shape
  the agent writing the plan needs, so it is stated here as well as in
  `ROADMAP.md` §0.2 — per root `CLAUDE.md`, the two must agree.
- **A plan is subject to the Writing Style**, like everything else written
  here. Referenced, not restated: root `CLAUDE.md` holds it.
