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

## Milestones

Nothing below is built. The repository today is scaffolding: build, test,
benchmark, lint, docs, and audit pipelines around placeholder functions.

| # | Milestone | Done when |
| --- | --- | --- |
| 1 | Simulation engine | Sequences simulate under a specified `(Q, t, π, τ)`; recovered summary statistics match their analytic expectations within stated tolerances. |
| 2 | Likelihood engine | Felsenstein pruning matches brute-force marginalization on small trees to machine precision, with benchmarks against the NumPy reference. |
| 3 | Continuous optimization | Branch lengths, `Q`, and `π` are fitted by gradient methods; gradients match finite differences; simulated parameters are recovered within their confidence intervals. |
| 4 | Move sets and a classical baseline | NNI and SPR neighbourhoods, plus hill-climbing search, reproducing published behavior on standard datasets. |
| 5 | Reinforcement learning agent | A learned proposal policy beats the hill-climbing baseline on held-out simulated datasets, measured by likelihood reached per likelihood evaluation. |
| 6 | Empirical validation | Results on real alignments compared against established inference tools, with the comparison recorded in the technical document. |

Milestones 1–3 are the engineering foundation; nothing about the RL question
can be answered honestly before they are in place and tested.

## Background reading

The technical document (`docs/tex/`) develops the theory and cites the
standard sources: Felsenstein's *Inferring Phylogenies* for substitution
models and tree search, Sutton & Barto for the RL formulation, MacKay for
inference and Monte Carlo, Goodfellow et al. and Prince for optimization and
automatic differentiation, and *Programming Massively Parallel Processors* for
the GPU kernels. `CLAUDE.md` lists them in full.
