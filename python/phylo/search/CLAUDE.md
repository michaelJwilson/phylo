# search/

Move sets over topologies, the agents that choose among them, and the
temperature schedules that shape the surface they walk.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

NNI, SPR, and multi-SPR neighbourhoods behind one interface; hill-climbing
and reinforcement-learning agents; annealing schedules and the
likelihood-versus-temperature curves used to judge exploration.

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
- **Every proposed move set states whether it is complete**, in which of the
  two senses, and what it costs per step.
