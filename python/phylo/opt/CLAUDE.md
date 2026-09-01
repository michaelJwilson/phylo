# opt/

Fits the continuous parameters — branch lengths, rate matrix, root
distribution — for an assumed topology, by gradient methods.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## Framework

**PyTorch**, decided. Its MPS backend is the mature path on Apple Silicon,
which the memory requirement in `ROADMAP.md` targets alongside CUDA. It is
not yet a dependency in `pyproject.toml`: it is added by the first PR whose
code imports it, per the repository's rule against declaring dependencies
ahead of their use.

## Local rules

- **Constraints by construction, not by projection.** Branch lengths through
  a log or softplus map, the root distribution through a softmax, rate
  parameters positive through a log map. An optimizer that has to be stopped
  from leaving the feasible set will eventually leave it.
- **Gradients are checked against central finite differences** with a stated
  step and tolerance. This is the test that catches a wrong derivative in the
  pruning recursion; nothing else does.
- **Recovery is the acceptance test.** Fit simulated data with known
  parameters and require the confidence intervals to cover the truth at the
  nominal rate. A likelihood that increases proves the optimizer runs, not
  that the model is right.
- **The likelihood must increase monotonically** under the optimizer, and a
  test says so.
