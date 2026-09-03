# opt/

Fits continuous parameters by gradient methods. The interface is
model-agnostic by construction: the same machinery serves phylogenetic
trees, HMMs and the Potts model (issue #63), and the phylogenetic case is
one instance of it rather than its author.

Root `CLAUDE.md` holds the repository-wide rules, and its **Writing Style**
section binds this file too — and every docstring, comment and commit message
in this module. It is referenced here, never restated. What follows is local.

## What lives here

`objective.py` is the interface — an unconstrained parameter vector, a
differentiable scalar to minimize, and a map back to named constrained
parameters. `constrain.py` holds the constraint maps every instance shares.

`fit.py` holds the optimizer and the interval machinery: L-BFGS with a
strong-Wolfe line search, and standard errors from the observed Fisher
information pushed through the constraint map by the delta method. The
intervals live here rather than in a test because a standard error computed
in a test is not available to the next instance.

`potts.py` and `hmm.py` are **reference instances**, not applications: a
1-D Potts chain in an external field and a discrete HMM, each with an exact
independent oracle for its own objective. They exist so the interface is
tested against something that is not a tree. The phylogenetic instance
belongs with them, as another instance.

`hmm.py`'s truth type (`HmmParams`) and its data generator live in
`phylo.sim.hmm`; this module imports the type and fits, but does not draw
data — the same split `potts.py`'s own generator is moving towards
(issue #170).

## Framework

**PyTorch**, per root `CLAUDE.md`. What that means here: constraints and the
optimizer below are written against its autograd, and the MPS backend is the
Apple Silicon path the memory requirement in `ROADMAP.md` assumes.

## Local rules

- **No application imports.** Nothing here may import from `phylo.sim`,
  `phylo.likelihood` or `phylo.search`. This is asserted by
  `tests/regression/test_opt_objective.py`, not left to review: a single
  convenience import turns the abstraction back into a phylogenetics-specific
  optimizer, and neither `ruff` nor `mypy` would notice.
- **Constraints by construction, not by projection.** Branch lengths through
  a log or softplus map, the root distribution through a softmax, rate
  parameters positive through a log map. An optimizer that has to be stopped
  from leaving the feasible set will eventually leave it.
- **Gauge-fix, or a fitted parameter has no value.** A softmax over `n`
  logits is invariant to adding a constant to all of them; a Potts field is
  invariant to the same shift. `constrain.log_simplex` pins the first logit
  so the map is a bijection onto the simplex. Without that the observed
  information is singular and a confidence interval is undefined.
- **Finite differences are the derivative test that matters here.** Root
  `CLAUDE.md` requires the check; this is the module where a wrong derivative
  in the pruning recursion surfaces, and nothing else catches it. The check
  is shared (`tests/_objective_checks.py`) and compares relative to the
  gradient's norm — entrywise relative fails at a symmetric starting point,
  where entries are exactly zero, and absolute does not transfer across data
  sizes.
- **Every threshold is relative, inside the optimizer too.** Convergence is
  the gradient's infinity norm against the objective's own magnitude, and
  L-BFGS's own `tolerance_grad`/`tolerance_change` are switched **off**: their
  defaults are absolute, so on a summed log-likelihood they halt the inner
  loop long before the gradient is small relative to the objective. That is
  issue #111's failure inside the optimizer rather than in a test.
- **A symmetric starting point can be a stationary point.** The HMM's uniform
  parameters are one: with every hidden state identical, the gradient in the
  initial and transition blocks is exactly zero, and a fit started there
  returns a one-state model while appearing to make progress. Starting points
  break the symmetry deterministically, and a test pins the reason.
- **Recovery is the acceptance test.** Fit simulated data with known
  parameters and require the confidence intervals to cover the truth at the
  nominal rate. A likelihood that increases proves the optimizer runs, not
  that the model is right. Where a model has an exact symmetry — permuting an
  HMM's hidden states leaves its likelihood unchanged — recovery is stated up
  to that symmetry, and the alignment is part of the test.

## Discrete moves are outside the interface

A discrete move changes the *structure* — a different topology, chain length
or state count — and so changes what the parameter vector means and how long
it is. It cannot be a step inside a fit over a fixed-length vector: it
constructs a **new** `Objective`. The loop that proposes moves owns that
construction and calls `fit` per candidate.

This is a seam, not a feature to build here. An optimizer that owned the
outer loop would have to know what a move is, which is the model knowledge
this module exists to exclude.
