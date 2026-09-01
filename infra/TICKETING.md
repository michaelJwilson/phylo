# Standing up the ticketing system

What this repository provides, and what has to be done by hand in GitHub's
interface. Splitting it this way is the point: everything a file can express
lives in a file, so the taxonomy cannot drift from the documentation, and only
the irreducibly manual steps are left to memory.

## In the repository

| Piece | File | State |
| --- | --- | --- |
| Issue form: outcome, why, submodule, scope, validation | `.github/ISSUE_TEMPLATE/task.yml` | ready |
| Label definitions — priorities, submodules, `approved`, `skip-changelog` | `.github/labels.yml` | ready |
| Workflow that applies those definitions | `.github/workflows/labels.yml` | ready, run manually |
| Priority semantics and the approval policy | `infra/CLAUDE.md`, `DEV.md` | ready |
| The `/approve` workflow itself | — | blocked, see below |

## Your steps, in order

1. **Merge this pull request**, so the template, definitions, and workflow
   exist on `main`.
2. **Run the Labels workflow**: Actions → *Labels* → *Run workflow*. It applies
   `.github/labels.yml` with `gh label create --force`, which is idempotent, so
   re-running it after editing the file is the supported way to change labels.
   Nothing else should create labels by hand.
3. **Check the default.** The issue template applies `priority:low`. Confirm on
   a scratch issue that it lands, then delete the issue.
4. **File the two standing tickets** — they are recurring work, not one-off
   tasks, so they are yours to own rather than something a PR can create:
   - *CLAUDE.md ingestion*: fold newly provided CLAUDE.md content into the
     repository's conventions, reconciling contradictions rather than
     appending.
   - *Roadmap ingestion*: fold newly provided roadmap suggestions into
     `ROADMAP.md` and `STATUS.md`, marking what each displaces.
5. **Decide on `anthropic/claude-code-action`.** The `/approve` automation
   cannot be built without it, and the allowed-actions list in
   Settings → Actions currently permits only `actions/*` and
   `dtolnay/rust-toolchain`. Approving it is a supply-chain decision, so it is
   recorded here rather than taken quietly.

## What follows, once step 5 is decided

A workflow triggered by an `issue_comment` containing `/approve`, gated on the
commenter's write permission, which posts a plan to the thread and opens a pull
request implementing it. The policy it enforces is already written down in
`infra/CLAUDE.md`: the pull request must implement a plan already posted, and a
flawed plan gets a revised plan in-thread rather than a silent correction.

Two guards belong in that workflow when it is built. It must refuse to run on
issues without the `approved` label, so a stray comment cannot start work. And
it must respect the priority labels rather than running everything immediately,
which is the only thing that makes `priority:low` mean anything.
