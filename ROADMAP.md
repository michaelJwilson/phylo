# ROADMAP

## 1. Goal & Specifications

Objective: Solve the large parsimony problem (search over phylogenetic tree topologies) using reinforcement learning,
optimizing a learned proposal policy to score (sub-tree compressed across sites) candidate trees by their (approximate/bounded)
likelihood more effectively than classical approaches.

Engineering Requirements:

- **Scale:** n ∈ [10,1000] taxa; L ∈ [100,11000] sites; k-state alphabets, e.g., 4 nucleotide.
- **Accuracy:** normalized Robinson–Foulds distance ≤0.05 against simulated truth; ΔlnL competitive to IQ-TREE 2 / RAxML-NG for equal time/system constraints.
- **Performance:** sub-second gradient updates at n=100.
- **Hardware & Memory:** O(n×L×k) memory footprint strictly bounded to 16 GB (Apple Silicon) or 24 GB (NVIDIA). Native dispatch required for CUDA, Metal/MPS, and CPU (for CI/CD).
- **Numerics:** cross-device support, e.g. wrt float discrepancies are managed via a defined tolerances, not bitwise equality that does not cross platforms.

## 2. Development Stages & Milestones

### Stage 1: The Engineering Foundation

Establishing the simulation, compression, and numerical infrastructure required to train and score any model.

- **Milestone 1: Simulation Engine.** Implement k-state, e.g. 4 alphabet models, assuming a given evolutionary model - Jukes-Cantor. Ensure generated sequences match analytic closed-form transition probabilities. Landed: the `k`-state Jukes-Cantor simulator (`phylo.sim.simulate`, `phylo.sim.jc`), validated against the closed-form transition probabilities within a declared Monte Carlo tolerance across several site and taxa sizes (issue #55).
- **Milestone 2: Compression & Canonicalization.** Implement lossless subtree-level (DAG) compression across sites.  Define and enforce a canonical newick topology key to enable O(1) equality checks. `phylo.sim.newick`'s topology counting and validation (issue #60) are a prerequisite for this key, not the key itself. That prerequisite landed (`count_topologies`, `validate_newick`, `validate_unrooted_newick`, `to_newick`); the canonical key itself (issue #73) and subtree/site DAG compression are not started.
- **Milestone 3: Likelihood Engine.** Implement Felsenstein pruning via PyTorch/Triton/JAX (GPU) and Rust (CPU). Validate against brute-force marginalization on small trees to machine precision. Rust CPU backend (`oxiphylo.pruning_log_likelihood`, `phylo.likelihood.pruning_rust`) landed, validated against both the NumPy oracle and brute-force marginalization; GPU dispatch (Triton/JAX) is not yet implemented.
- **Milestone 4: Continuous Optimization.** Fit branch lengths, rate matrix (Q), and root distribution (π) via autodiff. Validate gradients against finite differences and ensure simulated parameter recovery within confidence intervals. Landed: differentiable pruning (`phylo.likelihood.pruning_torch`), with branch lengths as a tensor separate from the topology and a general `rate_matrix` path via `torch.matrix_exp`, validated against `torch.autograd.gradcheck` and central finite differences of the NumPy oracle. Landed: the model-agnostic fitting interface and optimizer (`phylo.opt`), with constraints by construction, intervals from the observed Fisher information, and parameter recovery validated against known truth on two non-phylogenetic reference instances — a Potts chain and an HMM, the latter cross-checked against Baum–Welch (issue #63). Branch-length fitting against the simulation fixtures landed behind that same interface (issue #104), with the two branches below a rooted root fitted as their estimable sum; the performance requirement above is measured rather than asserted at 203 ms per gradient update for n=100, L=1000. The general time-reversible model (`phylo.sim.gtr`) supplies the free rate parameters Jukes–Cantor lacks, and its exchangeabilities and `π` are fitted and recovered alongside the branch lengths, so Milestone 4 is complete. Not started: rate variation across sites.

### Stage 2: Classical Baselines & Tracking

Stand up standard move sets for search and the rigid evaluation harness required to measure RL performance.

- **Milestone 5: Move Sets & Classical Baseline.** Implement strict NNI and SPR topological neighborhoods. Test connectivity via random walks and reproduce published hill-climbing behavior on standard datasets. NNI and SPR neighbourhood generators (`phylo.search.topology`) landed, validated exhaustively against closed-form neighbour counts at `n = 5..8` including NNI-in-SPR containment (issue #79, `changelog.d/79.added.md`). The classical hill-climbing baseline landed (`phylo.search.infer`, issue #117): NNI and SPR searches reach the exhaustively enumerated maximum and recover the generating topology from all 12 starting points on a 6-taxon fixture, at a median of 14 candidate fits for NNI against 48 for SPR. It did not need issue #73's canonical Newick key, which it was expected to depend on — `leaf_bipartitions` is rooting- and order-independent and serves as the deduplication key. Not started: the random-walk connectivity test, and reproduction on published datasets.
- **Milestone 6: Experiment Tracking.** Stand up a localized manifest system (e.g., Aim) to log configurations, likelihood traces, compute budgets, and QA figures. Ensure total reproducibility from a single manifest. Not started on `main`; PR #83 is an open draft adding `phylo.qa.ledger`.
- **Milestone 7: Benchmark Harness.** Deploy a leaderboard evaluating algorithms strictly on budget-matched log-likelihood metrics across shared seeds. Require statistical significance (paired comparisons) to claim new state-of-the-art variants.

### Stage 3: Reinforcement Learning (The Vanilla Application)

Replacing hand-designed heuristics with a learned proposal policy.

- **Milestone 8: RL Agent Deployment.** Frame the MDP (state: topology/parameters/alignment, action: NNI/SPR, reward: ΔlnL). Train a policy that strictly beats the classical hill-climbing baseline on held-out simulated datasets per evaluation budget. Partially landed (issue #131): the model-agnostic RL interface, a softmax-over-scored-actions policy, and REINFORCE with a baseline (`phylo.learn`), validated against an exact trajectory-enumeration oracle — the sampled estimator agrees with the enumerated gradient to 9.9e-03 relative over 6000 episodes, and a myopic variant is rejected at 71%. On the non-phylogenetic reference environment the learned policy beats hill climbing at a matched decision budget, reaching the enumerated optimum from 86.6% of starts against greedy's 80.2%, in 8 of 8 seeds. The phylogenetic environment landed too (`phylo.search.rl`), with the known-parameter reward validated against the fitted one it stands in for: on the 6-taxon fixture the two surfaces score the generating topology highest, agree on the best of all 105 topologies across a 50-fold range of the fixed branch length, and correlate at 0.9568, while a known-parameter score is ~300x cheaper than a fitted one. The comparison also showed the fitted surface does not totally order topologies — many candidates share a maximized likelihood because the branch distinguishing them is fitted to zero — so it is reported as a linear correlation rather than a rank one. Not started: PPO and a learned state-value baseline. The open obstacle is not machinery but a fixture — hill climbing already reaches the enumerated optimum from every start at 6 taxa, so nothing at a size exhaustive enumeration can referee separates a learned policy from the baseline.
- **Milestone 9: Empirical Validation.** Validate the RL agent on public, real-world biological alignments, documenting comparisons against IQ-TREE 2 and RAxML-NG in the technical document.

## 3. Blue Sky & Nice-to-Haves

Research extensions intended to drastically reduce likelihood evaluations, slated for post-vanilla implementation.

- **Tree Set Bounding:** Branch-and-bound implementations using relaxed pruning or coarse alignment compression to cheaply calculate upper likelihood bounds and prune massive branches of the search space.
- **Learned Compound Moves:** Replacing single NNI/SPR actions with temporally extended macro-actions sampled dynamically via a Dirichlet process.
- **Transformer Policy over Canonical Newick:** Tokenizing the canonical Newick DAG and training an LLM-style policy gradient network directly on the tree structure.
- **Advanced Move Sets (TBR & Multi-SPR):** Expanding the search neighborhood with Tree Bisection and Reconnection (TBR) and simultaneous k-composed SPR moves to escape deep local optima.
- **Stochastic Escape:** Implementing Metropolis-style accepted-worsening steps or ratchet-style site reweighting to brute-force out of likelihood valleys.
