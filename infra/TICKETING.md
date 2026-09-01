# The ticketing system

A ticket becomes a plan in its own thread, the plan is corrected in that
thread, and only then does it become a pull request. The point of the shape is
that the reviewable artefact arrives before the code: a plan is cheap to
reject, and a branch full of the wrong work is not.

## The loop

| Step | Who | What happens |
| --- | --- | --- |
| File a ticket | maintainer | `.github/ISSUE_TEMPLATE/task.yml`; `priority:low` by default |
| — | *Ticket plan* | A plan is posted to the thread automatically |
| `/edit <correction>` | maintainer | A **new** revised plan is posted; the old one stays |
| `/approve` | maintainer | The plan is approved and the ticket labelled `approved` |
| — | *Ticket approve* / *Ticket queue* | The work starts, now or at its scheduled slot |
| — | *Ticket run* | A branch, the checks, and a pull request that closes the ticket |

`/plan` re-plans a ticket from scratch — after the ticket text itself changes,
say. `/edit` revises the plan already posted.

Revisions accumulate rather than replace. `infra/CLAUDE.md` requires that a
flawed plan gets a revised plan in the thread rather than a silent correction,
so the thread is the record of what changed and why, and `/approve`
implements the last revision.

## What the commands cost you if they are wrong

Every command is maintainer-only, checked against `author_association` before
a runner starts, so a drive-by comment cannot spend tokens. Beyond that:

- **`/approve` refuses a ticket with no plan.** The workflow searches the
  thread for a comment beginning `<!-- phylo-plan -->` and fails if there is
  none. The policy that a pull request implements a plan already posted is
  therefore enforced, not just written down.
- **Approval is a label, not an event.** `approved` is what the queue reads,
  so a missed or delayed sweep loses nothing.
- **A failed run withdraws its own approval.** It swaps `approved` for
  `agent:blocked` and comments with the run URL. Without that the next sweep
  would pick the ticket straight back up and fail it again, on a loop, at full
  token cost. `/approve` again clears the block.

## When work starts

`infra/schedule.py` decides, and `tests/infra/test_schedule.py` pins it.

| Priority | Starts |
| --- | --- |
| `priority:high` | Immediately, from `/approve` |
| `priority:medium` | At the next sweep of *Ticket queue* (every two hours) |
| `priority:low` | At the first sweep outside 09:00–17:00 Princeton time |

Princeton observes daylight saving, so the window is evaluated in
`America/New_York` rather than against a fixed offset — at a fixed −05:00 the
summer window sits an hour wrong and low-priority work starts in the middle of
a working morning. The window is literal and has no weekday qualifier, because
the policy it implements has none: Saturday at noon is inside working hours.

## In the repository

| Piece | File |
| --- | --- |
| Issue form: outcome, why, submodule, scope, validation | `.github/ISSUE_TEMPLATE/task.yml` |
| Label definitions | `.github/labels.yml`, applied by `.github/workflows/labels.yml` |
| Plan and `/edit` | `.github/workflows/ticket-plan.yml` |
| `/approve` | `.github/workflows/ticket-approve.yml` |
| The implementation run | `.github/workflows/ticket-run.yml` |
| The priority queue | `.github/workflows/ticket-queue.yml` |
| When a priority may start | `infra/schedule.py` |
| Priority semantics and the approval policy | `infra/CLAUDE.md`, `DEV.md` |

## Your steps, in order

1. **Install the Claude GitHub App** on this repository, from
   https://github.com/apps/claude. The action mints a short-lived,
   repository-scoped token from it over OIDC, which is why every ticket job
   requests `id-token: write`.
2. **Allow the action.** Settings → Actions → General → Allowed actions
   currently permits `actions/*` and `dtolnay/rust-toolchain`; add
   `anthropics/claude-code-action@*`. This is the supply-chain decision, and
   the reason the workflows pin a commit SHA rather than the `v1` tag: a
   moving tag lets whoever can move it run code against this repository's
   token.
3. **Add the model credential** as a repository secret — either
   `ANTHROPIC_API_KEY` or `CLAUDE_CODE_OAUTH_TOKEN`. Exactly one; the
   workflows pass both inputs and the unset one expands to empty.
4. **Run the Labels workflow**: Actions → *Labels* → *Run workflow*. It
   applies `.github/labels.yml` with `gh label create --force`, which is
   idempotent, so re-running it after editing the file is the supported way to
   change labels. Nothing else should create labels by hand. The ticket
   workflows depend on `approved`, `agent:running`, and `agent:blocked`
   existing.
5. **Decide about `TICKET_PR_TOKEN`** — see below. It is optional, and the
   system works without it.
6. **Check the default.** File a scratch ticket, confirm `priority:low` lands
   and a plan is posted, then `/edit` it once to see the revision, and close
   the ticket.
7. **File the two standing tickets** — recurring work, so yours to own rather
   than something a pull request creates:
   - *CLAUDE.md ingestion*: fold newly provided CLAUDE.md content into the
     repository's conventions, reconciling contradictions rather than
     appending.
   - *Roadmap ingestion*: fold newly provided roadmap suggestions into
     `ROADMAP.md` and `STATUS.md`, marking what each displaces.

## Known limits

- **CI does not run on the pull request unless `TICKET_PR_TOKEN` is set.**
  GitHub deliberately does not raise workflow events for actions taken with
  `GITHUB_TOKEN`, so a pull request opened with it arrives with no checks —
  which is the one thing this repository's Definition of done cannot do
  without. Setting `TICKET_PR_TOKEN` to a fine-grained personal access token
  (contents: write, pull-requests: write, on this repository only) fixes it, at
  the cost of a long-lived credential in repository secrets. Without it, a
  maintainer starts the checks by pushing to the branch. Weigh it; neither
  answer is free.
- **Scheduled sweeps are best-effort.** GitHub delays `schedule:` triggers
  under load and disables them after 60 days without repository activity. The
  `approved` label survives both, and *Ticket queue* can be run by hand.
- **Prompt injection is bounded by the tool list, not eliminated.** A ticket
  body is untrusted text that goes into a prompt. The plan job can only read
  files and comment; the run job can write and push but cannot reach `main`,
  which branch protection blocks rather than the tool list. Read a plan before
  approving it — that is what `/approve` is for.
- **The token pin is a decision, not a default.** `anthropics/claude-code-action`
  is pinned to the commit `v1` pointed at on 2026-09-01. Bump it in a pull
  request, the way `uv.lock` is bumped, having read what changed.
