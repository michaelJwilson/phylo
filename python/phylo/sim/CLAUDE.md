# sim/

Generates alignments from a known model (e.g. evolutionary) according to a well
defined truth fully defined in a yaml.  Scientific validation is provided by test
according to the known true parameters and expected properties.

Root `CLAUDE.md` holds the repository-wide rules, and its **Writing Style**
section binds this file too — and every docstring, comment and commit message
in this module. It is referenced here, never restated. What follows is local.

## What lives here

Simulation of `k`-state, e.g. 4, characters down a binary tree under a rate matrix `Q`,
branch lengths `t`, and a root distribution `π`: the `k`-state Jukes–Cantor
model first, then the general time-reversible model (`gtr.py`) after.

`gtr.py` exists because Jukes--Cantor has no free rate parameters, so there
is nothing in `Q` or `pi` to fit under it. Its three normalizations are
gauges, not tidiness: each removes a direction along which the likelihood is
exactly flat, and a flat direction leaves the observed information singular
and every parameter without a confidence interval. `simulate_alignment` takes
an optional `rate_matrix`; omitting it keeps the Jukes--Cantor closed form,
because a substitution model is the last thing worth changing silently.

`newick.py` is the package's single source of Newick functionality (root
`CLAUDE.md`, "Package Surface"): serializing a tree (optionally with
per-node ancestral states) to Newick, validating a Newick string against
the rooted-binary-tree grammar, and counting distinct topologies for a
given taxon count. `tree.py` holds only the `Node` structure and
traversals; nothing outside `newick.py` builds or parses Newick strings.

`graph.py` and `potts.py` (issue #170) are the one part of this module
that names no phylogenetic application: a `PottsGraph` (nodes, a per-edge
coupling, an explicit boundary condition), an N-D lattice built as an
instance of it -- a 1-D chain is `lattice_graph((L,), ...)`, not a second
type -- and a `k`-state Potts sampler on top. An open 1-D chain has an
exact backward-message sampler; every other graph is sampled by
single-site Gibbs/heat-bath MCMC. `phylo.opt.potts.simulate_chains` builds
its 1-D chain on this rather than on its own copy of the recursion, which
is why `opt/CLAUDE.md` names these two submodules as its one exception to
"no application imports".

## Local rules

- **Validate against the analytic result, never against our own likelihood.**
  The technical document gives the closed form for `k`-state Jukes–Cantor
  transition probabilities.
- **Validation tests state their tolerance and run for a variety of site/taxa sizes according to 
goal: validation of benchmarking.**
