# Roadmap

## The goal

Solve the large parsimony problem — the search over phylogenetic tree
topologies — with reinforcement learning, scoring candidate trees by the
Felsenstein likelihood.

The search space is the obstacle. The number of unrooted binary topologies on
`n` taxa is `(2n − 5)!!`: about 2×10⁶ for 10 taxa, 2×10²⁰ for 20, and 3×10⁷⁴
for 50. Exhaustive evaluation is hopeless past a handful of taxa, so
established tools hill-climb from a starting tree, proposing local
rearrangements and keeping the ones that score better. The proposal policy in
those tools is fixed and hand-designed. This project asks whether a learned
policy does better.

## The model

A candidate is scored by its likelihood under a continuous-time Markov model
of character substitution, parameterized by:

- **a rate matrix** `Q`, governing substitution rates between states;
- **branch lengths** `t`, in expected substitutions per site;
- **a root distribution** `π`, the state probabilities at the root;
- **an assumed tree** `τ`, the topology under evaluation.

Branch transition probabilities follow `P(t) = exp(Qt)`, and the likelihood of
the observed characters is computed by Felsenstein's pruning algorithm — a
post-order traversal that marginalizes internal states in time linear in the
number of taxa, rather than exponential.

## The search

Moves come from the two standard rearrangement neighbourhoods:

- **NNI** (nearest-neighbour interchange) — swap the subtrees adjacent to an
  internal edge. Small, cheap, local.
- **SPR** (subtree prune and regraft) — detach a subtree and reattach it
  elsewhere. Larger neighbourhood, better at escaping local optima.

Framed as a Markov decision process: the state is the current topology with
its fitted continuous parameters and a summary of the alignment, an action is
a move drawn from the NNI or SPR neighbourhood, and the reward is the
improvement in maximized log-likelihood. An episode is one search trajectory
from a starting tree.

## Extensions to the move set

NNI and SPR over single moves are the starting point, not the destination.
Three extensions attack the same bottleneck — the number of likelihood
evaluations a search spends — and each is a research question rather than an
implementation task.

**Bound whole sets of trees, and rule them out.** Scoring every neighbour
exactly wastes work when most are poor. A cheap *upper* bound on the
likelihood attainable anywhere in a set of topologies lets the search discard
the entire set, branch-and-bound style: when the bound falls below the best
log-likelihood already found, no member of that set can win. Bounds can come
from relaxing the pruning recursion, or from compressing the alignment —
identical site patterns already collapse, and coarser encodings trade
tightness for speed. Soundness decides whether this is an optimization or a
bug: a bound that dips below an attainable likelihood silently discards the
optimum, so each candidate bound needs a proof and an exhaustive
small-tree search for counterexamples.

**Learn compound moves rather than single ones.** Composing several NNI or
SPR rearrangements into one action reaches topologies no single move reaches,
at the cost of a much larger action space — temporally extended actions, in
reinforcement-learning terms. Rather than fixing the composition depth,
draw it during training from a Dirichlet process, so the number of distinct
compound moves the agent maintains grows with the evidence for them instead
of being chosen in advance. The target is unchanged: fewer likelihood
evaluations for the same likelihood reached.

**Put a transformer on the tree string.** A topology serializes to a Newick
string, which a transformer can consume directly: tokenize the compressed
string, pretrain on simulated trees, then fine-tune the policy with standard
policy-gradient machinery — the ordinary industry recipe, applied to trees.
This rests on the canonical form defined in workstream 2 below: raw Newick is
not unique, and feeding a model many spellings of one topology teaches it
distinctions that carry no phylogenetic meaning.

The technical document states all three precisely; `CLAUDE.md`'s reference
list groups the sources they draw on.

## What it rests on

The RL layer is only as good as the machinery underneath it, which is where
the engineering effort goes:

- **Fast simulation.** Generating datasets under a known `(Q, t, π, τ)` gives
  ground truth for validity tests and training data for the policy. Training
  needs this at scale.
- **Fast likelihood evaluation.** Every proposed move costs at least one
  likelihood evaluation, so the pruning algorithm sits on the hottest path in
  the project. Per `CLAUDE.md`'s Performance rules, it goes to the GPU
  (PyTorch, Triton, or JAX) if the arithmetic earns 10x over the vectorized
  NumPy reference, and to the Rust backend otherwise.
- **Automatic differentiation.** Branch lengths, rate-matrix parameters, and
  the root distribution are continuous and optimized per topology. Gradients
  through the pruning recursion make that optimization tractable and give the
  RL layer a differentiable inner loop.
- **Validity, not plausibility.** Every layer is tested against simulated data
  with known parameters, and against independent computations — brute-force
  marginalization on small trees, finite-difference checks on gradients. See
  `CLAUDE.md`'s Testing section.

## Work breakdown

Six workstreams. Each states what it builds, what would count as done, and
the decision or risk that could sink it. Nothing here is implemented.

### 1. Simulate

Generate alignments from a known model, because every test downstream needs
data whose truth is known.

- **Alphabet.** A general `k`-state alphabet, not just DNA: `k = 4` for
  nucleotides, 20 for amino acids, 2 for binary characters, arbitrary `k`
  for the general case.
- **Models.** Jukes–Cantor generalized to `k` states (equal exchange rates,
  uniform root distribution), then K80, F81, HKY85, and GTR as the
  constraints are relaxed. Each is a constrained `Q`; the simulator takes
  `Q` and does not care which name it carries.
- **Trees.** Random binary topologies (uniform over topologies, or from a
  birth–death process), with branch lengths drawn from a stated
  distribution. Every draw seeded, so a dataset is reproducible from its
  seed alone.
- **Done when** simulated data match what the model implies analytically,
  not merely "look reasonable": the `k`-state Jukes–Cantor transition
  probabilities have a closed form (given in the technical document), and
  observed substitution frequencies must match it within Monte Carlo error
  at stated tolerances.
- **Risk.** A simulator that is wrong in the same way as the likelihood
  code validates nothing. The two must be written against the analytic
  result, not against each other.

### 2. Compress

Two distinct compressions, both exact, plus the canonical form the rest of
the project depends on.

- **Across sites.** Identical alignment columns collapse to one pattern with
  a multiplicity — standard, and the first large win.
- **Across subtrees.** A partial likelihood at a subtree depends only on the
  column *restricted to that subtree's leaves*. Sites that differ globally
  can agree on that restriction, so each subtree groups its sites by
  restricted pattern and computes once per distinct one. The win grows with
  depth, and the shared structure is exactly the "common subtree across
  sites" worth caching.
- **Representation.** Identical subtrees are shared rather than copied, so a
  tree is stored as a DAG, keyed by the canonical form below. A dictionary
  of recurring subtree motifs — an extended alphabet over the canonical
  string — shortens the encoding further and doubles as the tokenization the
  transformer policy consumes.
- **Canonical Newick.** Raw Newick is not unique: one topology has many
  spellings, differing by child order and by where the string is rooted. The
  canonical form fixes both. Root the unrooted tree at the leaf whose label
  is smallest under a fixed total order. Assign every subtree a key
  bottom-up: a leaf's key is its label, an internal node's key is the
  concatenation of its children's keys in sorted order. Emit children in
  that order. Branch lengths travel alongside as a vector in canonical node
  order, so one topology with two length assignments shares a topology key.
  The technical document states the algorithm.
- **Done when** compression is lossless — the likelihood computed from the
  compressed representation equals the uncompressed value to floating-point
  tolerance — and canonicalization passes two properties: two trees produce
  the same string exactly when they are the same topology (tested by
  randomly re-rooting and permuting children of one tree, and against
  distinct trees), and parsing a canonical string reproduces the tree it
  came from.
- **Payoff beyond size.** The canonical key is also the memo key for "have
  we already scored this topology?", which the search needs regardless of
  the transformer.

### 3. Fit

Maximize the likelihood over branch lengths, rate matrix, and root
distribution for an assumed tree, efficiently, on realistic simulated data.

- **Parameterization.** Constraints handled by construction: branch lengths
  through a log or softplus map, the root distribution on the simplex
  through a softmax, exchangeabilities positive through a log map, and the
  scale fixed by the normalization that makes branch lengths mean expected
  substitutions per site.
- **Gradients.** Reverse-mode automatic differentiation through the pruning
  recursion, in log space with per-node rescaling that must itself stay
  differentiable. Branch-length derivatives use the eigendecomposition of a
  reversible `Q`, so one decomposition serves every branch.
- **Frameworks.** PyTorch or JAX, per the performance rule in `CLAUDE.md`.
  Neither is a dependency of this project today, and adding one needs
  explicit permission first.
- **Optimizer.** A quasi-Newton or trust-region method for the standalone
  fit; a first-order method when the fit sits inside an RL training loop.
- **Done when** gradients match central finite differences, simulated
  parameters are recovered with confidence intervals covering the truth at
  the nominal rate, the likelihood increases monotonically under
  optimization, and the time per likelihood-and-gradient evaluation is
  reported at realistic `(n, m, k)`.

### 4. Move

Support several neighbourhoods behind one interface, and be precise about
what each guarantees.

| Move set | Neighbourhood size | Reaches every topology? | Cost and character |
| --- | --- | --- | --- |
| NNI | `2(n − 3)` | Yes | Cheapest step; local, and prone to stalling in poor optima |
| SPR | quadratic in `n` | Yes; every NNI is an SPR | Larger reach, escapes optima NNI cannot |
| multi-SPR (`k` composed) | the radius-`k` SPR ball | Yes, already at `k = 1` | Reshapes the traversal rather than the reachable set; cost grows fast with `k` |

**Two senses of "complete", routinely conflated.** *Connectivity* asks
whether repeated moves can reach every topology from any start: NNI, SPR and
TBR all can, so all three are complete in this sense, and multi-SPR adds no
reachability that SPR lacks. *Optimality* asks whether the search finds the
best tree: none of them guarantee that, because connectivity says nothing
about the landscape between. A hill climber stops at a local optimum under
its own move set, and a local optimum under NNI need not be one under SPR.
Only exhaustive enumeration, or branch and bound with a sound upper bound,
guarantees the optimum.

**Additional sets worth supporting**, and why:

- **TBR** (tree bisection and reconnection) — a strict superset of SPR:
  fewer local optima, more cost per step. The natural next rung.
- **Stochastic escape** — Metropolis-style accepted worsening steps, or
  ratchet-style site reweighting followed by re-search. Attacks local optima
  directly rather than by enlarging the neighbourhood.
- **Guided restriction** — propose only around edges a cheap proxy flags
  (parsimony change, quartet conflict). Efficiency rather than completeness:
  it shrinks a neighbourhood we already know is connected.
- **Recombination** — combine compatible splits from two good trees.
  Population-based search rather than a walk.
- **Exhaustive enumeration and branch and bound** — exact for small `n`, and
  the backstop that makes every other move set testable, since it supplies
  the true optimum to compare against.
- **Done when** each move set enumerates its neighbourhood exactly — checked
  against the closed-form counts where they exist, and against exhaustive
  enumeration for small `n` — and a random walk over small trees visits
  every topology, which is connectivity tested rather than asserted.

### 5. Track

One record per run, for both the fixed-tree problem and the search.

- **Both problems, one manifest.** Small parsimony (score or fit a given
  tree) and large parsimony (search over topologies) differ in what they
  vary, not in what needs recording.
- **Inputs recorded:** commit, `uv.lock` and `Cargo.lock` hashes, seed,
  dataset identity and hash, model specification, move set, hyperparameters,
  evaluation budget, and hardware.
- **Outputs recorded:** the likelihood trace against evaluation count, wall
  time, evaluation counts, the final tree as a canonical Newick string, and
  the figures and tables the QA framework emits.
- **Storage.** A run directory plus a machine-readable manifest this
  repository owns. A third-party tracker (MLflow, Weights & Biases) is a
  dependency decision that needs explicit permission, not a default.
- **Done when** a recorded run replays from its manifest alone and produces
  the same numbers — bitwise where seed and hardware permit, within stated
  tolerance otherwise — and the QA figures are generated from the run store
  rather than assembled by hand.

### 6. Benchmark

Rank variants, and keep a defensible current best.

- **What varies.** Each sub-algorithm is a variant plugged into one harness:
  compression scheme, likelihood-bound family, move set, policy
  architecture. Only the variant changes between runs.
- **Benchmark set.** Simulated instances with known truth spanning `n`, `m`,
  `k`, and rate heterogeneity, plus standard public alignments, each with a
  fixed likelihood-evaluation budget.
- **Metrics.** For the fixed-tree task: parameter error against the known
  truth, and time per likelihood-and-gradient evaluation. For search: best
  log-likelihood reached at a fixed evaluation budget, and evaluations
  needed to reach a target likelihood. Budget-matched, because every method
  wins given unbounded evaluations.
- **Statistics.** Several seeds per configuration, paired comparisons across
  the shared seeds, and an interval reported with every number. Search
  trajectories are correlated samples, so a naive standard error understates
  the spread and would rank noise.
- **The leaderboard.** A checked-in results file naming the current best per
  task, with the commit, seed set, and budget that produced it. A challenger
  replaces the holder only by beating it at equal budget across seeds *and*
  passing the validity tests — speed never buys a place on its own.
- **Where it runs.** On fixed hardware, never on CI runners: the variance
  that keeps benchmarks out of the CI gate today would equally corrupt a
  ranking.
- **Done when** each task's winner is reproducible from its recorded
  manifest, and adding a variant needs no change to the harness.

## Milestones

Nothing below is built. The repository today is scaffolding: build, test,
benchmark, lint, docs, and audit pipelines around placeholder functions.

| # | Milestone | Workstream | Done when |
| --- | --- | --- | --- |
| 1 | Simulation engine | 1 | Sequences simulate under a specified `(Q, t, π, τ)`; recovered substitution frequencies match the model's closed form within Monte Carlo error at stated tolerances. |
| 2 | Likelihood engine | 3 | Felsenstein pruning matches brute-force marginalization on small trees to machine precision, with benchmarks against the NumPy reference. |
| 3 | Compression and canonical form | 2 | Site- and subtree-level compression is lossless to floating-point tolerance; canonical Newick collides exactly on identical topologies and round-trips through the parser. |
| 4 | Continuous optimization | 3 | Branch lengths, `Q`, and `π` are fitted by gradient methods; gradients match finite differences; simulated parameters are recovered within their confidence intervals. |
| 5 | Move sets and a classical baseline | 4 | NNI, SPR, and multi-SPR enumerate their neighbourhoods exactly; connectivity is tested by random walk on small trees; hill-climbing search reproduces published behavior on standard datasets. |
| 6 | Run tracking | 5 | Any recorded run replays from its manifest alone and reproduces its numbers; QA figures are generated from the run store. |
| 7 | Reinforcement learning agent | 4, 5 | A learned proposal policy beats the hill-climbing baseline on held-out simulated datasets, measured by likelihood reached per likelihood evaluation. |
| 8 | Benchmark harness and leaderboard | 6 | Variants are ranked at equal budget across seeds with intervals reported; each task's winner is reproducible from its manifest. |
| 9 | Move-set extensions | 4, 6 | Bounds that provably never exclude an attainable optimum, learned compound moves, and a transformer policy over canonical Newick — each measured against milestone 7's agent at equal likelihood-evaluation budget. |
| 10 | Empirical validation | 6 | Results on real alignments compared against established inference tools, with the comparison recorded in the technical document. |

Milestones 1–4 are the engineering foundation; nothing about the RL question
can be answered honestly before they are in place and tested. Milestone 3
gates the transformer work in 9, which needs the canonical form, and gates
memoized search, which needs the topology key. Milestones 6 and 8 are what
make the later comparisons believable rather than anecdotal: 9 depends on 7
for the baseline it has to beat, and on 8 for the harness that judges it.

## Background reading

The technical document (`docs/tex/`) develops the theory and cites its
sources, which `CLAUDE.md` groups in full: **infrastructure** — software
craft, systems and hardware, algorithms and discrete mathematics, numerical
optimization — and **application** — phylogenetics and sequence analysis,
probabilistic inference and graphical models, statistical physics and Monte
Carlo, information and coding theory, the geometry of statistical models, and
learning and decision making. Felsenstein's *Inferring Phylogenies* carries
the substitution models and tree search, Sutton & Barto the RL formulation,
MacKay and Koller & Friedman the inference machinery, and *Programming
Massively Parallel Processors* the GPU kernels.
