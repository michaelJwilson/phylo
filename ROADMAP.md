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

- **Milestone 1: Simulation Engine.** Implement k-state, e.g. 4 alphabet models, assuming a given evolutionary model - Jukes-Cantor. Ensure generated sequences match analytic closed-form transition probabilities.
- **Milestone 2: Compression & Canonicalization.** Implement lossless subtree-level (DAG) compression across sites.  Define and enforce a canonical newick topology key to enable O(1) equality checks.
- **Milestone 3: Likelihood Engine.** Implement Felsenstein pruning via PyTorch/Triton/JAX (GPU) and Rust (CPU). Validate against brute-force marginalization on small trees to machine precision.
- **Milestone 4: Continuous Optimization.** Fit branch lengths, rate matrix (Q), and root distribution (π) via autodiff. Validate gradients against finite differences and ensure simulated parameter recovery within confidence intervals.

### Stage 2: Classical Baselines & Tracking

Stand up standard move sets for search and the rigid evaluation harness required to measure RL performance.

- **Milestone 5: Move Sets & Classical Baseline.** Implement strict NNI and SPR topological neighborhoods. Test connectivity via random walks and reproduce published hill-climbing behavior on standard datasets.
- **Milestone 6: Experiment Tracking.** Stand up a localized manifest system (e.g., Aim) to log configurations, likelihood traces, compute budgets, and QA figures. Ensure total reproducibility from a single manifest.
- **Milestone 7: Benchmark Harness.** Deploy a leaderboard evaluating algorithms strictly on budget-matched log-likelihood metrics across shared seeds. Require statistical significance (paired comparisons) to claim new state-of-the-art variants.

### Stage 3: Reinforcement Learning (The Vanilla Application)

Replacing hand-designed heuristics with a learned proposal policy.

- **Milestone 8: RL Agent Deployment.** Frame the MDP (state: topology/parameters/alignment, action: NNI/SPR, reward: ΔlnL). Train a policy that strictly beats the classical hill-climbing baseline on held-out simulated datasets per evaluation budget.
- **Milestone 9: Empirical Validation.** Validate the RL agent on public, real-world biological alignments, documenting comparisons against IQ-TREE 2 and RAxML-NG in the technical document.

## 3. Blue Sky & Nice-to-Haves

Research extensions intended to drastically reduce likelihood evaluations, slated for post-vanilla implementation.

- **Tree Set Bounding:** Branch-and-bound implementations using relaxed pruning or coarse alignment compression to cheaply calculate upper likelihood bounds and prune massive branches of the search space.
- **Learned Compound Moves:** Replacing single NNI/SPR actions with temporally extended macro-actions sampled dynamically via a Dirichlet process.
- **Transformer Policy over Canonical Newick:** Tokenizing the canonical Newick DAG and training an LLM-style policy gradient network directly on the tree structure.
- **Advanced Move Sets (TBR & Multi-SPR):** Expanding the search neighborhood with Tree Bisection and Reconnection (TBR) and simultaneous k-composed SPR moves to escape deep local optima.
- **Stochastic Escape:** Implementing Metropolis-style accepted-worsening steps or ratchet-style site reweighting to brute-force out of likelihood valleys.
