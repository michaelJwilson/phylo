# STATUS

Coverage ledger: what exists, what is only recorded as intent, and what is
untouched (`CLAUDE.md`, "Known Gaps"). The PR that changes an item's status
updates its row here; this is the single ledger — no second list is kept
elsewhere. Status values: **Done**, **Partial**, **Untouched**.

## Stage 1: The Engineering Foundation

| Milestone | Status | Notes |
| --- | --- | --- |
| 1. Simulation Engine | Done | `sim/jc.py` (JC transition probabilities and rate matrix), `sim/simulate.py` (k-state alignment simulation), `sim/params.py` (YAML-defined ground truth). Validated against the analytic closed form: `tests/regression/test_jc_validation.py`, `test_jc_simulate.py`. |
| 2. Compression & Canonicalization | Untouched | `sim/newick.py` provides topology counting (`count_topologies`) and Newick grammar validation (`validate_newick`) — prerequisites per `ROADMAP.md`. No canonical topology key or subtree-level DAG compression implemented. |
| 3. Likelihood Engine | Partial | NumPy oracle (`likelihood/pruning.py`) and independent brute-force cross-check (`likelihood/brute_force.py`) done, pinned to machine precision: `tests/regression/test_likelihood_pruning.py`, `test_likelihood_validation.py`. Differentiable PyTorch CPU backend (`likelihood/pruning_torch.py`) done, pinned against the NumPy oracle: `test_pruning_torch.py`, `test_pruning_torch_validation.py`. Rust CPU kernel, CUDA, and Metal/MPS dispatch not started — `src/lib.rs` exposes only a placeholder `double` binding. |
| 4. Continuous Optimization | Untouched | `opt/` holds only its `CLAUDE.md` and an empty `__init__.py`. No branch-length, rate-matrix, or root-distribution fitting. |

## Stage 2: Classical Baselines & Tracking

| Milestone | Status | Notes |
| --- | --- | --- |
| 5. Move Sets & Classical Baseline | Untouched | `search/` holds only its `CLAUDE.md` and an empty `__init__.py`. No NNI/SPR neighborhoods or hill-climbing agent. |
| 6. Experiment Tracking | Untouched | Aim is not yet a dependency (`infra/CLAUDE.md`); no run manifest exists. |
| 7. Benchmark Harness | Untouched | No leaderboard or paired-comparison evaluation exists. |

## Stage 3: Reinforcement Learning

| Milestone | Status | Notes |
| --- | --- | --- |
| 8. RL Agent Deployment | Untouched | No MDP framing, policy, or training loop. |
| 9. Empirical Validation | Untouched | No comparison against IQ-TREE 2 / RAxML-NG. |

## Supporting infrastructure

| Area | Status | Notes |
| --- | --- | --- |
| CLI (`scripts/run_phylo.py`) | Partial | Registered as the `run_phylo` console script; prints a placeholder message, no subcommands. |
| QA figures (`qa/`) | Partial | `sim_tree.py`, `sim_example.py`, `sim_problem_sizes.py`, `figure.py` render `sim/` output for the technical document. No `likelihood/`, `opt/`, or `search/` figures yet, blocked on those modules. |
| Rust extension (`oxiphylo`) | Partial | PyO3 module builds and is tested (`tests/test_oxiphylo_bindings.py`); exposes only the placeholder `double` binding, no numerical kernel. |
| CI (`DEV.md`) | Done | Eight required jobs (`lint`, `rust-lint`, `rust-tests`, `build`, `python-tests`, `docs`, `technical-doc`, `audit`) enforced per `DEV.md`. |
| Technical document (`docs/tex/`) | Partial | Covers the Canonical Newick form and k-state JC transition probabilities. Pruning, optimization, and search algorithms not yet documented. |

## Known gaps

- `python/phylo/oxiphylo.pyi` is hand-written and can drift from the compiled extension; run `python -m mypy.stubtest phylo.oxiphylo` periodically (`DEV.md`, "Known Gap").
