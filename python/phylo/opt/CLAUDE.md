# opt/

Fits the continuous parameters — branch lengths, rate matrix, root
distribution — for an assumed topology, by gradient methods.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## Framework

**PyTorch**, per root `CLAUDE.md`. What that means here: constraints and the
optimizer below are written against its autograd, and the MPS backend is the
Apple Silicon path the memory requirement in `ROADMAP.md` assumes.

## Local rules

- **Constraints by construction, not by projection.** Branch lengths through
  a log or softplus map, the root distribution through a softmax, rate
  parameters positive through a log map. An optimizer that has to be stopped
  from leaving the feasible set will eventually leave it.
- **Finite differences are the derivative test that matters here.** Root
  `CLAUDE.md` requires the check; this is the module where a wrong derivative
  in the pruning recursion surfaces, and nothing else catches it.
- **Recovery is the acceptance test.** Fit simulated data with known
  parameters and require the confidence intervals to cover the truth at the
  nominal rate. A likelihood that increases proves the optimizer runs, not
  that the model is right.
