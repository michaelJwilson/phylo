# ROADMAP

### Stage 0: Goal & Specifications

Implement modern solvers for mixed discrete/continuous optimization, e.g. in the context of the large parsimony problem — search over optimized phylogenetic tree topologies —
with autodiff, reinforcement learning (learning a proposal policy that scores candidate trees) by exact, approximate or bounded likelihoods more effectively than classical approaches.

Requirements:

- **Accuracy:** validation of simulation and results against truth, e.g. normalized Robinson–Foulds distance ≤0.05 for defined problems; ΔlnL competitive with simple oracles on    
  small problems, with known truth for large problems and in the future, external standard tools, e.g.,IQ-TREE 2 / RAxML-NG under equal time and system constraints.
- **Scaling & Hardware:** O(n×L×k) memory footprint bounded to 16 GB (Apple Silicon) or 24 GB (NVIDIA). Native dispatch supported for CUDA, Metal/MPS, and CPU (for CI/CD).  Cross-  
  device agreement is checked against a declared tolerance, `float32` and `float64` where possible, otherwise `float32` (metal), not bitwise.

## 1. Development Stages & Milestones to standup a minimal implementation

Anticipated milestones include the specification, the status, the evidence and the issue.

### Stage 1: The Foundation

The simulation and infrastructure needed to train and validate computationally efficient models, i.e. Benchmark problems:
wrt the discrete/continuous optimization abstraction, we will benchmark three sets of problems, phylogenetic trees, 2D/N-D
Potts models in an external field and HMMs.  Problems sizes cover both realizations, and sites, e.g. n ∈ [10,1000] taxa;
L ∈ [100,11000] sites; 4 nucleotides.  These will be used for validation against known truth, benchmarking and ablation studies.

We maintain an academic paper that showcases results and provides appendices with the necessary background (at the level of PhD notes),
for the methods and results achieved.

- **Milestone 1: Simulation Engine.** Implement fixtures for the anticipated problems, e.g. k-state alphabet models for a given evolutionary model (first,
  Jukes-Cantor, 2D Potts, ...).  Validate the simulations by known properties, e.g. analytic closed-form transition probabilities.

- **Milestone 2: Likelihood Engine.** Implement Likelihoods, e.g. Felsenstein pruning, via PyTorch/Triton/JAX (GPU) and Rust (CPU). Validate against brute-force
  marginalization on small fixtures to the required tolerance.  Maintain an application-agnostic fitting interface that maintains the required API.

- **Milestone 3: Continuous Optimization.** Implement solvers for the continuous half, e.g. fit branch lengths, rate matrix (Q), and root distribution (π) with modern autodiff engines.  Validate gradients against finite differences, recover simulated parameters within confidence intervals, etc.

- **Milestone 5: Discrete move sets & classical baseline for supported application ** Implement e.g, strict NNI and SPR topological neighbourhoods, together with ICM, Wolff algorithm, etc.

### Stage 2: Reinforcement Learning

Replacing standard heuristics with learned policies and variational models.

- **Milestone 1: RL Agent Deployment.** Frame the MDPs (e.g., state: topology/parameters/alignment, action: NNI/SPR, reward: ΔlnL).
- establish RL environments for the required applications;
- update the technical discussion with detailed breakdowns of suitable algorithms and a discussion of their relative pros/cons, to each other and to classical. 
- Train a policy that strictly beats classical baselines on held-out simulated datasets per an evaluation budget.

- **Milestone 2: Empirical Validation.** Validate the RL agent against standard approaches on small problem sizes and benchmark against known truth and external tools for large problems.

  - **Milestone 3: Alation studies, Experiment Tracking & Leaderboard ** Stand up a localized manifest system (e.g. Aim) logging configurations, e.g. commit, likelihood traces, compute budgets, and QA figures, so a run reproduces from a single manifest. Deploy a leaderboard evaluating algorithms for ablation studies on budget-matched log-likelihood metrics across shared seeds. Require paired comparisons to reach significance before claiming a new state-of-the-art variant.

## 3. Blue Sky

Research extensions aimed at reducing the number of likelihood evaluations a search spends, slated for post-vanilla implementation.

- **Learned Compound Moves:** Replacing single NNI/SPR actions with temporally extended macro-actions sampled from a Dirichlet process.
- **Stochastic Escape:** Metropolis-style accepted-worsening steps, or ratchet-style site reweighting, to leave a likelihood valley.
- **Transformer Policy over Canonical Newick:** Tokenizing the canonical Newick DAG and training an LLM-style policy-gradient network on the tree structure.
- ...
