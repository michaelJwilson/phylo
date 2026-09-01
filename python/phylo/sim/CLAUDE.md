# sim/

Generates alignments from a known model and keeps the truth that generated
them. Everything downstream is tested against data produced here, so an error
in this module is invisible everywhere and fatal everywhere.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

Simulation of `k`-state characters down a tree under a rate matrix `Q`,
branch lengths `t`, and a root distribution `π`: the `k`-state Jukes–Cantor
model first, then K80, F81, HKY85, and GTR as the constraints relax. The
simulator takes a `Q` and does not care which name it carries.

## Local rules

- **Validate against the analytic result, never against our own likelihood.**
  The technical document gives the closed form for `k`-state Jukes–Cantor
  transition probabilities. A simulator checked against the pruning code it
  feeds would agree with it whenever both are wrong in the same way.
- **Truth ships with the data.** A dataset is `(alignment, Q, t, π, τ, seed)`
  or it is not a dataset. Losing the parameters that generated an alignment
  makes it useless for everything except a demo.
- **Every draw is seeded** with `np.random.default_rng(seed)`, and the seed is
  recorded, so any dataset is reproducible from its manifest alone.
- **Statistical tests state their tolerance and their sample size.** "Within
  Monte Carlo error" is a number here, not a hope.
