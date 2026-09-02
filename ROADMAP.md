# Roadmap

## 1. Goal

Solve the large parsimony problem — the search over phylogenetic tree
topologies — with reinforcement learning, scoring candidate trees by their
likelihood under a substitution model.

The search space is the obstacle. The number of unrooted binary topologies on
`n` taxa is `(2n − 5)!!`: 2×10⁶ at `n` = 10, 3×10⁷⁴ at `n` = 50. Exhaustive
evaluation is hopeless, so established tools hill-climb from a starting tree,
proposing local rearrangements and keeping improvements. This project asks
whether a learned proposal policy does better at equal evaluation budget.

## 2. Requirements

Every number is a target to be measured, not an assumption. The right-hand
column names what settles it; a requirement with no way to check it is not a
requirement.

### Problem size

| Dimension | Range |
| --- | --- |
| Taxa `n` | 10 – 1,000 |
| Sites `L` | 100 – 10,000 |
| States `k` | 4 (nucleotide), 20 (amino acid), general `k` |

### Targets

| Requirement | Target | Settled by |
| --- | --- | --- |
| Topology accuracy | Normalized Robinson–Foulds ≤ 0.05 vs. simulated truth | M9, at stated `n`, `L`, and model |
| Likelihood | `Δ ln L` within noise of IQ-TREE 2 and RAxML-NG at equal wall clock | M9 |
| Gradient step | < 1 s at `n` = 100, `L` = 1,000 | M3 benchmark |
| Amortized search | Total time to resolve a tree below classical hill-climbing, training included | M9 |
| Memory | `O(n × L × k)` partials within 16 GB unified or 24 GB GPU | M5 |
| Hardware | CUDA and Metal/MPS both first-class; CPU path sufficient for CI | M5 |
| Cross-device agreement | A stated numeric tolerance, never bitwise | **Open — see below** |

Three of these are not yet checkable, and each blocks the milestone that
would check it:

- **The accuracy targets name tools the project cannot run.** IQ-TREE 2 and
  RAxML-NG are not dependencies and no harness invokes them. Until M9 stands
  one up, "competitive" is unfalsifiable.
- **The cross-device tolerance states no number.** Root `CLAUDE.md` says the
  tolerance is "stated once in the technical document"; `docs/tex/` says only
  "within floating-point tolerance". M5 cannot accept or reject a backend
  until someone writes the number down.
- **The memory bound constrains a constant, not an order.** Partials at
  `n` = 1,000, `L` = 10,000, `k` = 4 are ~320 MB in float64 — comfortably
  inside 16 GB. What is not is the autodiff tape, which retains intermediates
  across the whole pruning recursion. The binding question is the retention
  factor, and gradient checkpointing is the lever. M3 must report it.

## 3. Milestones

Ordered so that correctness precedes speed and speed precedes search.
Nothing is optimized before there is an oracle to say it is still right.

| # | Milestone | Depends on |
| --- | --- | --- |
| **Stage 1 — a likelihood worth trusting** | | |
| M1 | Simulation engine | — |
| M2 | Differentiable likelihood | M1 |
| M3 | Continuous parameter fitting | M2 |
| **Stage 2 — scale** | | |
| M4 | Canonicalization and compression | M2 |
| M5 | Accelerated backends | M2, M4 |
| **Stage 3 — classical search** | | |
| M6 | Move sets | M4 |
| M7 | Hill-climbing baseline | M3, M5, M6 |
| M8 | Experiment tracking | M7 |
| M9 | Benchmark harness | M7, M8 |
| **Stage 4 — reinforcement learning** | | |
| M10 | RL proposal policy | M9 |

### Stage 1 — a likelihood worth trusting

**M1. Simulation engine.** Generate `k`-state characters down a tree under a
rate matrix `Q`, branch lengths `t`, and root distribution `π`; `k`-state
Jukes–Cantor first, then K80, F81, HKY85, GTR as constraints relax.
*Done when* simulated substitution frequencies match the closed-form
transition probabilities in `docs/tex/` within a stated Monte Carlo error at
a stated sample size, and every dataset carries `(alignment, Q, t, π, τ,
seed)`.

**M2. Differentiable likelihood.** Felsenstein pruning in PyTorch, with
per-node rescaling accumulated in log space inside the autodiff graph.
*Done when* it agrees with brute-force marginalization over internal states
at `n ≤ 6` to machine precision; rescaled and unrescaled paths agree; and
analytic gradients match central finite differences.

**M3. Continuous parameter fitting.** Fit `t`, `Q`, and `π` by gradient
methods, constrained by construction — log or softplus for branch lengths,
softmax for `π`, log for rate parameters. *Done when* fitting M1 data with
known truth recovers parameters with confidence intervals covering that truth
at the nominal rate over a stated number of replicates, and the gradient-step
and memory-retention benchmarks in §2 are reported.

### Stage 2 — scale

**M4. Canonicalization and compression.** A canonical Newick form fixing
rooting and child order, plus lossless site- and subtree-level (DAG)
compression. *Done when* the canonical key is invariant under relabeling and
rerooting, gives O(1) topology equality, and compressed and uncompressed
likelihoods agree exactly with the compression ratio reported.

**M5. Accelerated backends.** Rust/CPU, CUDA, and Metal/MPS behind one
interface, with the vectorized NumPy implementation retained as the oracle.
*Done when* every backend agrees with that oracle within the cross-device
tolerance — once §2's open number is fixed — and a benchmark table reports
each against it. *Blocked on that number.*

### Stage 3 — classical search

**M6. Move sets.** NNI and SPR neighborhoods behind one interface.
*Done when* neighborhood sizes match their closed forms (NNI: `2(n − 3)`),
a random walk visits every topology at `n ≤ 10` where exhaustive enumeration
is the oracle, and each move set states whether it is complete and at what
per-step cost.

**M7. Hill-climbing baseline.** The classical search the RL agent must beat.
*Done when* it reproduces published hill-climbing behavior on a standard
dataset and its likelihood trace is recorded per evaluation, not per
wall-clock second.

**M8. Experiment tracking.** Aim, self-hosted. *Done when* a run is
replayable from its manifest alone — commit, both lockfile hashes, seed,
dataset identity, model, move set, evaluation budget, hardware.

**M9. Benchmark harness.** Budget-matched comparison across shared seeds,
including an in-repo Robinson–Foulds implementation tested against
hand-computed cases, and a runner for IQ-TREE 2 and RAxML-NG. *Done when*
the §2 accuracy targets can be evaluated, and any state-of-the-art claim
rests on a paired test at stated significance.

### Stage 4 — reinforcement learning

**M10. RL proposal policy.** MDP over topologies — state: topology, fitted
parameters, alignment summary; action: a move from the M6 neighborhoods;
reward: `Δ ln L`. *Done when* the policy beats M7 on held-out simulated data
at equal evaluation budget, then on public biological alignments with the
comparison documented in `docs/tex/`.

> **Open conflict.** `python/phylo/search/CLAUDE.md` defines the reward
> differently — likelihood improvement *plus a terminal penalty for the gap
> to truth on reaching a local maximum*. This file and `docs/tex/` say
> `Δ ln L` alone. The two are not equivalent and M10 cannot begin until one
> is chosen.

## 4. Blue sky

Research extensions to cut likelihood evaluations, after the vanilla agent
works.

- **Tree-set bounding.** Branch-and-bound over relaxed pruning or coarse
  alignment compression, to rule out whole regions cheaply.
- **Learned compound moves.** Temporally extended macro-actions sampled from
  a Dirichlet process, replacing single NNI/SPR steps.
- **Transformer policy over canonical Newick.** Tokenize the M4 canonical
  form and train a policy-gradient network on the tree structure directly.
- **Wider neighborhoods.** TBR and simultaneous k-composed SPR, to escape
  deep local optima.
- **Stochastic escape.** Metropolis-style accepted-worsening steps or
  ratchet-style site reweighting.
