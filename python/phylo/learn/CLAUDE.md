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

`relaxed.py` is the Gumbel-softmax half of `ROADMAP.md` Stage 3's
differentiable-search bullet, and only that half: it relaxes Potts
configurations and HMM state paths, whose optima are enumerable, and leaves
tree topologies to the tropical Grassmannian line in `TICKETS.md`, which has
no oracle at any interesting size. `RelaxedObjective` is the seam — the
estimators, the exact gradient and the optimizer are written against it, so a
third discrete space costs one objective and not a second optimizer.

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

- **A relaxation must reduce to the discrete objective at the corners,
  exactly.** Checked over *every* configuration of a small instance to the
  float64 bound, not spot-checked. A relaxation that disagrees at a one-hot is
  a different model, and every measurement made against it transfers to
  nothing. The HMM case is checked across a module boundary — `phylo.learn`
  may not import `phylo.likelihood`, so `RelaxedHmmPath.discrete` and
  `phylo.likelihood.hmm_paths.path_log_probability` are genuinely independent
  implementations of the same quantity.

- **`E_q[score] = score(q)` for a multilinear objective, and the boundary is
  multilinearity — not the chain.** Under a factorized `q` each term's
  expectation is that term at the marginals, so the relaxed form at the
  marginals *is* the expected discrete score. Two plausible statements of the
  limit are false and are refuted by tests: it is not that the model must be a
  chain (a lattice is equally multilinear), and it is not that terms must be
  pairwise (three *distinct* sites is still one factor per site). What breaks
  it is a term using one site twice, since `E[X**2] = E[X]` for an indicator —
  measured at 1.000 against 0.557. That is not hypothetical: `PottsGraph`
  permits a doubled bond, which after a periodic wrap at extent 2 joins a node
  to itself.

- **The relaxation adds no optimum the discrete problem lacks.** A multilinear
  function on a product of simplices attains its maximum at a vertex, so the
  relaxed optimum cannot exceed the discrete one. Everything a relaxed search
  loses is lost to local optima of the ascent, never to the relaxation, and a
  test pins the inequality over 200 random simplex points.

- **A gradient estimator's bias is measured against the exact gradient, never
  assumed small.** Enumeration gives `d E_q[score] / d logits` exactly at these
  sizes, so the bias-variance trade is a measurement. Measured over 20000
  draws, scaled by the largest exact component: bias falls from 0.598 at
  `tau = 2.0` to 0.036 at `tau = 0.1` while the standard deviation rises from
  0.165 to 3.39 — a factor of 17 against a factor of 21, so no temperature is
  good at both. Straight-through's bias matches the soft estimator's within
  error and its variance is higher at every temperature, so on this problem it
  buys nothing.

- **Averaging is variance reduction and never bias reduction**, so the two are
  reported separately. A method failing because of bias cannot be fixed by
  drawing more samples, and reporting one number hides which failure it is.

- **The sampling is what costs here, not the relaxation.** Against single-flip
  hill climbing on a chain whose optimum requires coordinated flips, over 40
  shared seeds: greedy 5/40, deterministic relaxation 18/40 (McNemar
  `p = 0.00098`), soft Gumbel-softmax 11/40 and straight-through 11/40 (both
  `p = 0.18`), annealed soft 11/40 (`p = 0.18`). The deterministic ascent —
  which the identity above licenses, so it is not a shortcut — is
  significantly better; adding Gumbel noise gives that up for a tie, and
  annealing does not recover it. It is also 15% cheaper per run (43.6 ms
  against 50.1 ms for 100 steps).

- **A tie is reported as a tie.** #193 set that precedent for the tree policy
  and it holds here: three of the four variants tie with the baseline, and
  saying so is worth more than promoting one on an unpaired difference.

- **A fixture whose optimum every method finds measures nothing.** The
  repository's `potts_params.yaml` has `J = 0.75 > 0`, so its optimum is
  `argmax(h)` repeated and greedy, the relaxation and random guessing all
  reach it. The comparison above uses an antiferromagnetic chain with two
  nearly-degenerate states instead. This is the third time this has come up —
  #177, #198, and #209's planted spin glass — and it is why the baseline is
  run first, before any claim is made.
