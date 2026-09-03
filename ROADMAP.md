# ROADMAP

## 1. Goal & Specifications

Objective: solve the large parsimony problem — search over optimized
phylogenetic tree topologies — with reinforcement learning and autodiff,
learning a proposal policy that scores candidate trees by an exact,
approximate or bounded likelihood more effectively than classical approaches.

Engineering Requirements:

- **Scale:** n ∈ [10,1000] taxa; L ∈ [100,11000] sites; k-state alphabets, e.g. 4 nucleotide.
- **Accuracy:** normalized Robinson–Foulds distance ≤0.05 against simulated truth; ΔlnL competitive with IQ-TREE 2 / RAxML-NG under equal time and system constraints.
- **Performance:** sub-second gradient updates at n=100.
- **Hardware & Memory:** O(n×L×k) memory footprint bounded to 16 GB (Apple Silicon) or 24 GB (NVIDIA). Native dispatch required for CUDA, Metal/MPS, and CPU (for CI/CD).
- **Numerics:** cross-device agreement is checked against a declared tolerance, never bitwise — `float32` and `float64` differ across CPU, CUDA and Metal, and a bitwise test does not survive the crossing.

## 2. Development Stages & Milestones

Each milestone states its specification, then its status. A status names what
landed, the issue that landed it, and the measurement that supports it.

### Stage 1: The Engineering Foundation

The simulation, compression, and numerical infrastructure needed to train and
score any model.

- **Milestone 1: Simulation Engine.** Implement k-state alphabet models under a given evolutionary model — Jukes-Cantor. Ensure generated sequences match the analytic closed-form transition probabilities.

  **Status: complete.** The `k`-state Jukes-Cantor simulator (`phylo.sim.simulate`, `phylo.sim.jc`), validated against the closed-form transition probabilities within a declared Monte Carlo tolerance across several site and taxa sizes (issue #55).

- **Milestone 2: Compression & Canonicalization.** Implement lossless subtree-level (DAG) compression across sites. Define and enforce a canonical Newick topology key for O(1) equality checks.

  **Status: prerequisite only.** `phylo.sim.newick`'s topology counting and validation landed (`count_topologies`, `validate_newick`, `validate_unrooted_newick`, `to_newick`, issue #60). The canonical key (issue #73) and subtree/site DAG compression are not started. Note that issue #117's search did not need the key: `leaf_bipartitions` is rooting- and order-independent and serves as the deduplication key.

- **Milestone 3: Likelihood Engine.** Implement Felsenstein pruning via PyTorch/Triton/JAX (GPU) and Rust (CPU). Validate against brute-force marginalization on small trees to machine precision.

  **Status: CPU only.** The Rust backend (`oxiphylo.pruning_log_likelihood`, `phylo.likelihood.pruning_rust`) landed, pinned against both the NumPy oracle and brute-force marginalization. GPU dispatch (Triton/JAX) is not started.

- **Milestone 4: Continuous Optimization.** Fit branch lengths, rate matrix (Q), and root distribution (π) via autodiff. Validate gradients against finite differences and recover simulated parameters within confidence intervals.

  **Status: complete.** Differentiable pruning (`phylo.likelihood.pruning_torch`) holds branch lengths as a tensor separate from the topology and takes a general `rate_matrix` through `torch.matrix_exp`, checked against `torch.autograd.gradcheck` and central finite differences of the NumPy oracle. The model-agnostic fitting interface and optimizer (`phylo.opt`, issue #63) impose constraints by construction, derive intervals from the observed Fisher information, and recover known parameters on two non-phylogenetic reference instances — a Potts chain and an HMM, the latter cross-checked against Baum–Welch. Branch-length fitting landed behind that interface (issue #104), with the two branches below a rooted root fitted as their estimable sum. The general time-reversible model (`phylo.sim.gtr`) supplies the free rate parameters Jukes–Cantor lacks; its exchangeabilities and `π` are fitted and recovered alongside the branch lengths. The performance requirement above is measured rather than asserted: 203 ms per gradient update at n=100, L=1000. Not started: rate variation across sites.

### Stage 2: Classical Baselines & Tracking

Standard move sets, and the evaluation harness that measures RL performance
against them.

- **Milestone 5: Move Sets & Classical Baseline.** Implement strict NNI and SPR topological neighbourhoods. Test connectivity via random walks and reproduce published hill-climbing behaviour on standard datasets.

  **Status: partial.** The neighbourhood generators (`phylo.search.topology`, issue #79) are validated exhaustively against closed-form neighbour counts at `n = 5..8`, including NNI-in-SPR containment. The hill-climbing baseline landed (`phylo.search.infer`, issue #117): on a 6-taxon fixture both move sets reach the exhaustively enumerated maximum and recover the generating topology from all 12 starting points, at a median of 14 candidate fits for NNI against 48 for SPR. Not started: the random-walk connectivity test, and reproduction on published datasets.

- **Milestone 6: Experiment Tracking.** Stand up a localized manifest system (e.g. Aim) logging configurations, likelihood traces, compute budgets, and QA figures, so a run reproduces from a single manifest.

  **Status: not started** on `main`; PR #83 is an open draft adding `phylo.qa.ledger`.

- **Milestone 7: Benchmark Harness.** Deploy a leaderboard evaluating algorithms on budget-matched log-likelihood metrics across shared seeds. Require paired comparisons to reach significance before claiming a new state-of-the-art variant.

  **Status: not started.**

### Stage 3: Reinforcement Learning (The Vanilla Application)

Replacing hand-designed heuristics with a learned proposal policy.

- **Milestone 8: RL Agent Deployment.** Frame the MDP (state: topology/parameters/alignment, action: NNI/SPR, reward: ΔlnL). Train a policy that strictly beats the classical hill-climbing baseline on held-out simulated datasets per evaluation budget.

  **Status: partial** (issue #131). The model-agnostic RL interface, a softmax-over-scored-actions policy, and REINFORCE with a baseline (`phylo.learn`) are checked against an exact trajectory-enumeration oracle: the sampled estimator agrees with the enumerated gradient to 9.9e-03 relative over 6000 episodes, and a myopic variant is rejected at 71%. On the non-phylogenetic reference environment the learned policy beats hill climbing at a matched decision budget, reaching the enumerated optimum from 86.6% of starts against greedy's 80.2%, in 8 of 8 seeds.

  The phylogenetic environment landed too (`phylo.search.rl`), with its known-parameter reward validated against the fitted one it stands in for. On the 6-taxon fixture the two surfaces score the generating topology highest, agree on the best of all 105 topologies across a 50-fold range of the fixed branch length, and correlate at 0.9568, while a known-parameter score costs ~300x less than a fitted one. That comparison also showed the fitted surface does not totally order topologies — many candidates share a maximized likelihood because the branch distinguishing them is fitted to zero — so it is reported as a linear correlation rather than a rank one.

  Not started: PPO and a learned state-value baseline. The open obstacle is a fixture rather than machinery: hill climbing already reaches the enumerated optimum from every start at 6 taxa, so no problem small enough for exhaustive enumeration to referee separates a learned policy from the baseline.

- **Milestone 9: Empirical Validation.** Validate the RL agent on public biological alignments, documenting comparisons against IQ-TREE 2 and RAxML-NG in the technical document.

  **Status: not started.**

## 3. Blue Sky & Nice-to-Haves

Research extensions aimed at reducing the number of likelihood evaluations a
search spends, slated for post-vanilla implementation.

- **Tree Set Bounding:** Branch-and-bound using relaxed pruning or coarse alignment compression to compute upper likelihood bounds cheaply, discarding whole regions of the search space.
- **Learned Compound Moves:** Replacing single NNI/SPR actions with temporally extended macro-actions sampled from a Dirichlet process.
- **Transformer Policy over Canonical Newick:** Tokenizing the canonical Newick DAG and training an LLM-style policy-gradient network on the tree structure.
- **Advanced Move Sets (TBR & Multi-SPR):** Expanding the neighbourhood with Tree Bisection and Reconnection and with simultaneous k-composed SPR moves, to escape deep local optima.
- **Stochastic Escape:** Metropolis-style accepted-worsening steps, or ratchet-style site reweighting, to leave a likelihood valley.
