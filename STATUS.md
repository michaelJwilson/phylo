# Status

What exists, what is recorded as intent, and what is untouched. This file
stands in for a project board: one place to see coverage, versioned with the
code it describes.

**Verified at `63cb516`** by reading the tree, not from memory.

| Marker | Meaning |
| --- | --- |
| **done** | Merged. The rule, policy, or code is in `main`. |
| **plan** | Recorded in `ROADMAP.md` as intended work. Nothing enforces it yet. |
| **open** | In an open pull request. |
| **—** | Unaddressed. Not written down anywhere. |

**done** covers a policy as readily as an implementation, and the two are not
the same thing. Where a rule exists but nothing enforces it, the note says so.

## Keeping this true

A status file that lies is worse than none, and this one goes stale the moment
a PR merges. So it follows the rule already applied to `README.md`,
`CLAUDE.md`, and `CHANGELOG.md`: **the PR that changes an item's status
updates its row, in the same PR.** A PR that closes a gap and leaves the row
reading "—" is incomplete.

Two habits keep the cost low. Update the `Verified at` line whenever the whole
file is re-checked, so a reader knows how much to trust the rest. And record
an item as **plan** only when `ROADMAP.md` genuinely carries it — an aspiration
in a pull-request description is not coverage.

## Hardware and numerics

| Item | Status | Notes |
| --- | --- | --- |
| CUDA and Metal/MPS both native | done | Requirement in `ROADMAP.md`; dispatch owned by `likelihood/` |
| Efficient CPU path when no GPU is present | done | Required, not a fallback — it is what CI runs |
| `float32`/`float64` cross-device tolerance policy | done | `ROADMAP.md` and `likelihood/CLAUDE.md`: agreement is a tolerance, never bitwise |
| The tolerance value itself | — | The policy defers to the technical document, which states no number |

## Reward, temperature, and learning design

| Item | Status | Notes |
| --- | --- | --- |
| Reward: climb under an evaluation budget; terminal penalty against truth; truth never a training signal | done | `search/CLAUDE.md`. Conflicts with `ROADMAP.md` — see Known inconsistencies |
| Temperature for smoothing the likelihood surface | done | Named as `search/`'s responsibility; the design is unwritten |
| Learned adaptive temperature schedules | — | |
| Likelihood-versus-temperature curve for the best local maximum, and contrasting new exploration against it | — | |
| Transformer over canonical Newick | plan | `ROADMAP.md` extensions, and the technical document |
| GNN over the canonical DAG | — | Only the transformer variant is recorded |
| Surrogate scoring: critic ranks many moves, top-K reach the exact evaluator | — | |
| Curriculum across n = 10 → 50 → 100+ | — | |
| Upper bounds that rule out whole sets of trees | plan | `ROADMAP.md` extensions, and the technical document |
| Lower bounds | — | Only upper bounds are covered; they serve different purposes |
| Compound moves drawn from a Dirichlet process | plan | `ROADMAP.md` extensions, and the technical document |

## Architecture

| Item | Status | Notes |
| --- | --- | --- |
| Application concerns separable from infrastructure | done | The module split, and the same axis in the reference taxonomy |
| `sim/`, `likelihood/`, `opt/`, `search/`, `infra/` | done | Directories exist; no code in them yet, deliberately |
| Per-submodule `CLAUDE.md` | done | Five files, each pinning what is local to its module |
| One set of interfaces serving an HMM and a Potts model in an external field, with test cases and benchmarks for both | — | This is what stops the interfaces silently becoming phylogenetics-only, so it wants writing down before they exist |

## Requirements

| Item | Status | Notes |
| --- | --- | --- |
| n ∈ [10, 1000]; L ∈ [100, 10 000] | done | `ROADMAP.md` requirements |
| Robinson–Foulds ≤ 0.05 against simulated truth | done | RF to be implemented here; an external implementation is a later cross-check |
| Δ ln L competitive with IQ-TREE 2 / RAxML-NG at equal wall clock | done | Stated as a target. Nothing can measure it — see Known inconsistencies |
| Sub-second gradient updates at n = 100; amortized search | done | `ROADMAP.md` requirements |
| `O(n × L × k)` within 16 GB unified or 24 GB GPU | done | The constraint that binds the compression workstream |

## Ticketing and the agentic process

| Item | Status | Notes |
| --- | --- | --- |
| Priorities: high immediate, medium at token refresh, low outside 09:00–17:00 Princeton, low by default | done | Policy in `infra/CLAUDE.md`; no labels exist |
| `/approve` posts a plan, then opens a PR implementing it | done | Policy only; the workflow is not built |
| A flawed plan gets a revised plan in-thread, not a silent fix | done | `infra/CLAUDE.md` |
| Tickets tagged by submodule | done | Policy only |
| Tickets batched and staged against the roadmap | done | Policy only; no batching mechanism |
| The `/approve` workflow itself | — | Needs `anthropics/claude-code-action`, which the allowed-actions list does not permit |
| Issue templates and label definitions | — | PR #13 carries an older scheme on stale history |
| Standing ticket: `CLAUDE.md` ingestion | — | |
| Standing ticket: roadmap ingestion | — | |
| Standing ticket: redundancy sweep — duplicate likelihood evaluations, fragmented canonicalization, code paths that drifted apart across PRs | — | |
| Fortnightly release: pull requests reviewed individually *and collectively* by a stronger model | — | |
| A changelog that survives parallel merges | — | Fragments were declined; `CHANGELOG.md` has now conflicted on three separate merges |

## CI guardrails

| Item | Status | Notes |
| --- | --- | --- |
| Topological move tests capped at n ≤ 10 | done | `DEV.md` CI budget, restated in `search/` and `infra/` |
| Performance never ranked in GitHub Actions | done | `DEV.md` CI budget |
| Long-running validity tests release-gated | done | Policy only; no release workflow enforces it |
| The workflow that runs those tests on release | — | |
| Audits removed from `pre-commit` | done | They reach the network and build `cargo-audit` |
| Git settings for CI/CD: branch auto-deletion, protection, required checks, token scope | done | `DEV.md` repository settings |

## Tooling

| Item | Status | Notes |
| --- | --- | --- |
| PyTorch for autodiff | done | Decided; enters `pyproject.toml` with the first code that imports it |
| Aim for experiment tracking | done | Decided; same deferral |
| DendroPy | plan | A later cross-check for our own Robinson–Foulds, not a dependency |
| AliSim, Pyvolve, Seq-Gen | — | Workstream 1 currently assumes we write the simulator ourselves |
| tskit, ETE Toolkit | — | tskit is worth studying for the compression work even if it never becomes a dependency |
| IQ-TREE 2 and RAxML-NG as containerized baselines | — | Named as the accuracy target; nothing runs them |
| UShER, PhyML | — | |
| Hydra for configuration; SLURM with Submitit for orchestration | — | |

## Literature

| Item | Status | Notes |
| --- | --- | --- |
| Azouri et al. (2024) — DQN over SPR, handcrafted features, published benchmarks | — | The closest prior work, and what this project claims to improve on, is cited nowhere in the repository |
| Gumbel MuZero / AlphaZero; PhyloGFN; Neal's tempered transitions | — | |
| The reported "within 0.969" figure | — | Dimensionally ambiguous; resolve before it becomes a target |

The reference list in `CLAUDE.md` carries 25 books and no papers, so adding
these means a new subsection rather than new entries.

## Known inconsistencies

Cross-document drift, as opposed to work not yet done. Each is live in `main`.

1. **The reward is defined twice, differently.** `ROADMAP.md`'s "The search"
   gives the reward as the improvement in maximized log-likelihood.
   `search/CLAUDE.md` gives it as improvement under an evaluation budget with
   a terminal penalty against truth. The second is the intended design; the
   first is what a reader of the roadmap would build.
2. **The tolerance policy has no number.** Cross-device agreement is defined
   as "a tolerance, fixed once and stated in the technical document," and the
   technical document states none. Until it does, the policy cannot settle the
   argument it exists to prevent.
3. **An accuracy target names tools nothing can run.** Δ ln L competitive with
   IQ-TREE 2 and RAxML-NG is a requirement, but no harness invokes either and
   containerizing them is unaddressed. The requirement is unmeasurable.
