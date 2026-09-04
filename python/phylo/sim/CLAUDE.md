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

`hmm.py` draws a hidden state path and its emitted observations jointly from
a declared `(pi, A, B)`, retaining the path alongside the data on the same
footing as `simulate.py`'s ancestral states. `phylo.opt.hmm` imports the
truth type (`HmmParams`) from here but draws no data itself — fitting and
generation are split the same way `opt/CLAUDE.md` splits them for every
reference instance.

`graph.py` holds `PottsGraph`, a general undirected graph carrying a
per-edge coupling, and `lattice_graph`, which builds an N-D lattice as a
constructed case of it — a 1-D chain is `lattice_graph((L,), ...)`, not a
separate type. The boundary is a `BoundaryCondition` rather than a string,
so an unrecognized one is a type error at the call site instead of a
constructor raising at run time; the yaml loader is the single place a
string becomes one. `PottsGraph` checks its own invariants on construction
— one coupling per edge, every edge naming a node that exists — because
every consumer indexes the spin array by node and the coupling array by
edge position, so a mismatch is a silently wrong energy rather than an
`IndexError`. `potts.py` draws spin configurations on a `PottsGraph`: a
graph recognized as a 1-D open chain is sampled exactly, by the same
backward-message recursion `phylo.opt.potts.log_partition` sums via
transfer matrix; every other graph is sampled by single-site Gibbs
(heat-bath) MCMC, as `n_samples` independent chains rather than one long
thinned chain, so a Python-level loop runs once per sweep rather than once
per sample. `phylo.opt.potts`'s own `simulate_chains` cannot import this
module (`opt/CLAUDE.md`'s "no application imports" rule covers all of
`phylo.sim`), so it keeps an independent copy of the exact open-chain
recursion rather than delegating to it — a duplication issue #186 tracks
resolving, by moving `PottsParams`/`load_potts_params` here the way issue
#171 moved the HMM's truth type.

## Local rules

- **A drawn ensemble reaches structures a hand-built fixture does not.**
  Belief propagation was tested on a connected tree, a connected lattice and a
  fully edgeless graph; everything between was unexercised. Over 120
  Erdos-Renyi draws, 104 carried an isolated vertex — the case sitting on the
  boundary between the general message-passing loop and the edgeless special
  case, and one no committed fixture reached. Where a property should hold
  across a *class* of graphs, draw the class.

- **`erdos_renyi_graph` takes a generator, never a seed.** An ensemble seeded
  per call is the same graph repeatedly, which looks like a passing test over
  many draws and is one draw. That mistake has been made here before
  (`phylo.qa.rl_reward_surface`), so the signature makes it impossible rather
  than warning against it.

- **No asymptotic graph result is testable at this scale.** The
  giant-component threshold at `p = 1/n` and the connectivity threshold at
  `ln(n)/n` hold in the limit; at the `n <= 10` cap `infra/CLAUDE.md` sets so
  enumeration stays affordable they say nothing. Check the property *per
  draw* — acyclicity by union-find, not by a limit theorem — so the oracle
  stays enumeration.


- **Validate against the analytic result, never against our own likelihood.**
  The technical document gives the closed form for `k`-state Jukes–Cantor
  transition probabilities.
- **Validation tests state their tolerance and run for a variety of site/taxa sizes according to 
goal: validation of benchmarking.**
