# search/

Move sets over topologies, the agents that choose among them, and the
temperature schedules that shape the surface they walk.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

NNI, SPR, and multi-SPR neighbourhoods behind one interface; hill-climbing
and reinforcement-learning agents; annealing schedules and the
likelihood-versus-temperature curves used to judge exploration.

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
