# learn/

Reinforcement learning over discrete search problems. The interface is
model-agnostic by construction, on exactly the terms `opt/CLAUDE.md` sets:
the same machinery must serve a Potts landscape and a tree search (issue
#131), and the phylogenetic case is one instance of it rather than its
author.

Root `CLAUDE.md` holds the repository-wide rules, and its **Writing Style**
section binds this file too — and every docstring, comment and commit message
in this module. It is referenced here, never restated. What follows is local.

## What lives here

`environment.py` is the interface — a state, an action set that varies with
the state, a step returning the next state and a reward, and features of each
available action. `policy.py` holds the softmax-over-scored-actions policy
the technical document specifies.

`rollout.py` generates episodes two ways, under a policy and under the greedy
searcher, through the same loop: a comparison between them is only meaningful
if the loop is shared.

`reinforce.py` is the score-function estimator. `exact.py` is its oracle —
expected return and its gradient by enumerating trajectories.

`potts.py` is a **reference instance**, not an application: single-flip local
search over the same 1-D Potts chain `phylo.opt.potts` fits. That is
deliberate rather than convenient. One model appears here as an *environment*
searched discretely and there as an *objective* fitted continuously, so the
claim that both halves of this project share one abstraction is demonstrated
rather than asserted.

## Local rules

- **No application imports.** Nothing here may import from `phylo.sim`,
  `phylo.likelihood` or `phylo.search`, asserted by
  `tests/regression/test_learn_environment.py`. An agent developed against a
  tree is an agent shaped by trees, and the phylogenetic environment
  therefore lives in `phylo.search`, which may import both halves.
  `phylo.opt` is not forbidden: it is infrastructure too, and reusing its
  Potts fixture is the point rather than a shortcut.
- **A reward is a closed form at known parameters, never an inner solve.**
  This is issue #131's simplification and the reason an RL loop is
  affordable: a fitted reward costs one L-BFGS solve per action, and a single
  episode evaluates the whole neighbourhood at every step. Where the fitted
  reward is the honest one, the two must be *compared* rather than swapped
  silently — the cheap surface can rank candidates differently from the
  maximized one.
- **`gamma = 1`, and it is not a hyperparameter.** The reward is a difference
  of the objective, so the undiscounted return telescopes to the total
  improvement an episode achieved. Any `gamma < 1` breaks that and prefers
  improvement found early over the same improvement found late.
- **A feature constant across a state's actions is unidentifiable.** The
  policy is a softmax over scores, so a constant shared by every action
  cancels — the same gauge `phylo.opt.constrain.log_simplex` fixes. No
  environment supplies a bias term, and a test pins the invariance.
- **The greedy searcher must be inside the policy class.** On the Potts
  landscape the reward decomposes exactly into the two features, so the
  weight vector proportional to `(J, 1)` *is* hill climbing at zero
  temperature. That is what makes "the agent beat the baseline" a statement
  about learning rather than about two unrelated algorithms, and a test
  checks the two produce identical trajectories.
- **A sampled return is a diagnostic, never a result.** It is a Monte Carlo
  estimate under a changing policy, so it rises for reasons that include a
  broken estimator. Learning is claimed against the enumerated expected
  return in `exact.py`; the training curve is reported, not asserted on.
- **The estimator is pinned to a brute-force gradient.** With a finite action
  set and a finite horizon the trajectory set is finite, so the expected
  return is a closed form and its gradient follows by autodiff. Both routes
  are checked — autodiff against finite differences, and the sampled
  estimator against the enumerated gradient — because a score-function
  estimator with a sign error is wrong by a factor and still trains.
- **The baseline must not depend on the batch it centres.** Subtracting a
  constant is unbiased because it multiplies a term of zero expectation, and
  that argument needs independence. A within-batch mean is correlated with
  the returns it centres and buys variance at the price of an `O(1/N)` bias;
  the running mean of *earlier* iterations costs nothing and keeps the claim
  exact.
- **A budget is counted in decisions, never in seconds.** Both the greedy
  searcher and a policy score the whole neighbourhood per decision, so
  decisions are the unit at which they are comparable — the same reasoning
  that makes `phylo.search.infer` count candidate fits.

- **An episode that may leave a local optimum is scored on its best state,
  not its last.** `rollout(..., stop_at_local_optimum=False)` runs to its
  budget, so its final state is wherever the walk happened to stop, and a
  real search keeps the best thing it saw. Scoring the last state instead
  would make a better searcher look worse the longer it ran.

- **A comparison against a wandering searcher is against *restarts*.** Once
  an episode is no longer bounded by reaching a local optimum, a single
  greedy run is not a budget-matched baseline: greedy stops after a few
  decisions and leaves the rest of the budget unspent. Restarting it until
  the budget is gone is the honest comparison, and on the issue #177 fixture
  it reaches the enumerated maximum from every start at 60 decisions, where
  the best epsilon measured reaches 0.908 (issue #194). A result stated
  against single-run greedy alone overstates itself.

## Framework

**PyTorch**, per root `CLAUDE.md`, and `float64` throughout: the exact
oracle compares autodiff against central finite differences, which `float32`
cannot support.

## The instances

Three, and the count is the point. `phylo.opt.Objective` earns its
model-agnosticism by carrying four instances that required no change to
`phylo.opt`; an interface justified by one model is shaped by that model.
`potts.py` holds the Potts landscape over a chain *or* an arbitrary graph —
one class with two constructors, since only the adjacency differs — and
`hmm.py` the hidden Markov state path, whose objective is a decoding problem
rather than an energy. The tree lives in `phylo.search`, which may import
both halves.

None of them takes an application type. A `PottsGraph` and an `HmmParams`
are unpacked by the caller into edge indices and log-probability arrays,
because the no-application-imports rule above admits no exception for
convenience.

## What is not here yet

PPO and a learned state-value critic. Issue #131 stages them; `docs/tex`'s
reinforcement-learning section states the theory they are built against.
