# search/

Move sets over topologies, the agents that choose among them, and the
temperature schedules that shape the surface they walk.

Root `CLAUDE.md` holds the repository-wide rules, and its **Writing Style**
section binds this file too — and every docstring, comment and commit message
in this module. It is referenced here, never restated. What follows is local.

## What lives here

NNI, SPR, and multi-SPR neighbourhoods behind one interface; hill-climbing
and reinforcement-learning agents; annealing schedules and the
likelihood-versus-temperature curves used to judge exploration.

`maxflow.py` and `maxflow_rust.py` are the exact ground-state solver: Dinic's
max flow, and the reduction that turns a two-state ferromagnetic Ising energy
into a minimum cut. The Python one is the oracle and stays; the Rust kernel
(`src/maxflow.rs`) is 28-34x faster measured on its own, and 6.6-10.6x as a
caller sees it — the difference being the list marshalling that crosses the
FFI boundary, the same gap #202 closes for the categorical sampler.

`alpha_expansion.py` extends that to any label count, as a sequence of binary
cuts, and carries the single-site descent baseline it has to beat. It is the
only thing here with a *proved* approximation bound.

`max_cut.py` reads the same model from the other side: maximizing the weight
of separated edges is minimizing the energy with every coupling negative,
which is the NP-hard side of `maxflow.py`'s boundary. It carries the
Goemans-Williamson relaxation and the 0.87856 guarantee that comes with it.

`potts_mcmc.py` holds the Potts lattice's Monte Carlo move sets --- single-site
heat bath, Swendsen-Wang, Wolff --- and `statistics.py` the two statistics they
are judged by. Those are samplers rather than optimizers, and the distinction
is the point: they are validated by the distribution they converge to, and
nothing there claims to find a ground state.

`infer.py` is the outer loop, and the first user of the seam `opt/CLAUDE.md`
records: a discrete move changes the structure being fitted, so it builds a
new `Objective` rather than stepping inside a fit. That is why this module
may import `phylo.likelihood` and `phylo.opt` while neither may import it —
the dependency runs application to infrastructure, and `phylo.opt` needed no
change to serve a topology search.

`rl.py` is the phylogenetic instance of `phylo.learn`'s `Environment`, here
for the same reason: `learn/` may import no application module, so the tree
environment cannot live beside the estimator that consumes it.

## Local rules

- **Topological tests run at `n <= 10`**, because at that size exhaustive
  enumeration is available as the oracle. A move test at `n = 50` proves
  nothing extra. `DEV.md`'s CI budget states the limit; this is why it is the
  right one.
- **Neighbourhood generators are verified against counts.** NNI has
  `2(n - 3)` neighbours; multi-SPR at radius `k` is the `k`-ball. Where a
  closed form exists, the test uses it; otherwise exhaustive enumeration.
- **Connectivity is tested, not assumed.** A random walk over small trees
  must visit every topology. Reaching every tree and finding the best tree
  are different claims — only exhaustive search or a sound bound gives the
  second.
- **Truth is a terminal penalty, never a training signal.** The reward climbs
  the likelihood as fast as the evaluation budget allows and pays the gap to
  truth on reaching a local maximum under all moves. An agent that can see
  the true tree during training learns to look it up.
- **A search budget is counted in candidate fits, never in seconds.**
  `DEV.md` forbids ranking performance on CI hardware, and a wall-clock
  budget would make a result depend on the machine that produced it, so a run
  would not be reproducible from its seed. Measured here: one candidate fit
  is 213 ms against 22 us to generate an entire NNI neighbourhood, so the fit
  is the only unit worth counting.
- **A topology is scored at most once per search.** `leaf_bipartitions` is
  the key — rooting- and child-order-independent, so the same tree proposed
  by two different moves is recognized. An SPR neighbourhood overlaps its
  predecessor heavily, and refitting is the dominant avoidable cost.
- **Every proposed move set states whether it is complete**, in which of the
  two senses, and what it costs per step.
- **Submodularity is the boundary, and it is refused rather than
  approximated.** A minimum cut gives the *exact* ground state for two states
  with every coupling non-negative. A negative coupling makes the energy
  non-submodular and the problem NP-hard; more than two states is not a cut
  problem at all, but alpha expansion (issue #207) with this as its inner
  solver. Both are raised, because a lattice-shaped wrong answer is
  indistinguishable from a right one at any size worth solving.

- **A uniform field makes the ferromagnetic ground state trivial.** Every
  coupling favours agreement and every site prefers the same state, so the
  answer is `argmax(h)` everywhere. The problem only has content with a
  *per-node* field — which is also the shape alpha expansion needs, since its
  binary sub-problem reads a data term off the current labelling. A benchmark
  or a test built on the uniform case is measuring nothing.

- **An approximation with a bound states the bound and measures the gap.**
  Alpha expansion's local minimum is within `2 c_max / c_min` of the global
  one for a metric pairwise term — exactly 2 for a uniform Potts coupling.
  That is the first claim here that holds at *every* size rather than only
  where enumeration reaches, so it is the thing to report; the realized ratio
  is measured beside it (39 of 40 runs found the optimum outright) rather
  than the bound being quoted as if it were the result.

- **A construction error in a cut does not break loudly.** Swapping the
  terminal capacities, or mis-costing an auxiliary node, yields a labelling
  that is merely *worse* — indistinguishable from the algorithm doing badly
  on a hard problem. Both errors were present in the first draft of
  `alpha_expansion.py` and passed every enumeration test at `3x3`. What
  caught them is the **reduction**: at two labels one expansion is exact, so
  it must reproduce `maxflow`'s minimum cut energy for energy. Any new cut
  construction here needs an equivalent reduction to something already
  validated, not only an enumeration.

- **A certificate states what it actually certifies.** Goemans-Williamson's
  0.87856 assumes the semidefinite relaxation is solved to optimality. This
  repository has no SDP solver, so `max_cut.py` solves it approximately by
  Burer-Monteiro gradient ascent, and the value it returns can sit *below* the
  relaxation's optimum — which makes a ratio measured against it optimistic.
  The symptom is measurable and is asserted rather than glossed: on a
  bipartite graph, where the optimum is exactly `|E|`, the ratio comes out
  slightly *above* 1, which an exact solve could never produce. Where
  enumeration reaches, the realized ratio is measured against the true
  optimum instead, and that is the number to trust.

- **A bipartite fixture cannot separate a good solver from a lucky one.** Its
  maximum cut is every edge, so anything that finds the two colour classes is
  optimal — which includes a solver that is broken in ways a triangle would
  expose. Lattices are bipartite, so the instances that do the work in
  `test_max_cut.py` are random graphs with odd cycles.

- **A sampler is validated by its distribution, never by inspection.** At an
  enumerable size the exact Boltzmann distribution is available, so a move set
  is tested by a chi-square goodness-of-fit against it at a declared
  significance and chain length. Cluster sizes looking plausible, or a chain
  visibly moving, is what a sampler with a broken accept step also does.
- **A goodness-of-fit test must be thinned, and the thinning is part of the
  test.** A chi-square assumes independent draws and successive sweeps are
  not: run on every sweep it rejects a *correct* sampler — measured at
  p = 0.038 for single-site and p = 0.0024 for Swendsen-Wang on chains that
  are right. Move sets that do different amounts of work per sweep need
  different thinning, or the comparison rejects whichever was thinned less.
- **A sweep must not stop on a state-dependent condition.** Each Monte Carlo
  step preserves the target distribution, but composing a *number* of them
  chosen from the outcome does not. Sizing a Wolff sweep by running clusters
  until their cumulative size reached the site count gave an aligned two-site
  chain 0.384 per aligned state against an exact 0.334: aligned states make
  large clusters, so they reached the budget sooner and were randomized less.
- **In an external field a cluster move needs an accept step.** The
  Fortuin-Kasteleyn construction is exact at zero field only; recolouring a
  cluster changes the field term by `|C| * (h_new - h_old)`, which the bond
  construction knows nothing about. Without the Metropolis correction the
  sampler runs, looks right, and converges to the wrong distribution — so
  every distributional test here is run with a field as well as without.
- **A cheap reward is a different surface, not a noisy estimate of the
  expensive one.** Scoring a candidate at fixed known parameters is what
  makes RL affordable — measured at roughly 300x a fitted score — but "the
  known parameters" do not transfer across topologies, because a branch
  length belongs to an edge and a different topology has different edges.
  Only a scalar carries over. So the two surfaces are *compared*
  (`phylo.qa.rl_reward_surface`) rather than assumed interchangeable, and the
  comparison is rerun when the fixture changes: agreeing on the argmax is the
  property that licenses training on the cheap one, and it is not guaranteed
  by the correlation being high.
- **The fitted surface does not totally order topologies.** Many candidates
  share a maximized log-likelihood to within the optimizer's convergence,
  because the branch that would distinguish them is fitted to zero and the
  tree collapses to the same polytomy. Their relative order is not a property
  of the model, so any statistic that depends on it — a rank correlation
  above all — is unstable across machines and is not a measurement. Report
  comparisons with a statistic continuous in the scores.
