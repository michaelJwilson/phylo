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

`canonical.py` holds the problem instances whose answer is known from outside
this repository, and it is governed by an admission rule rather than by taste
— see the two clauses under Local rules. Three live there: the triangular
Ising antiferromagnet, whose ground-state energy is a closed form at every
size; a planted Viana–Bray spin glass, which carries a state of known energy
past the point enumeration reaches; and a two-state HMM on which Viterbi and
posterior decoding return different answers. `triangular_lattice_graph` in
`graph.py` is the generator the first is built on — the square lattice plus
one diagonal per cell, which is what introduces the 3-cycles.

Nothing in `canonical.py` performs inference. Each entry is a construction
plus the quantity known about it in advance; the oracles that consume them
live in `phylo.likelihood` and `phylo.search`, which is the second admission
clause made structural.

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

- **A fixture is admitted on two clauses, and both are load-bearing.** Its
  answer must be known from *outside* this repository — a closed form, a
  published result, or an enumeration sharing no code with what it tests — and
  more than one module must consume it. The first stops the suite filling with
  cases that only re-test what already passes: #177's tree fixture was built
  because hill climbing solved every earlier one, and #198 then measured
  random-restart greedy solving *it* at 1.000. The second decides what belongs
  in `canonical.py` rather than in a module's own ticket; Rosenbrock is
  consumed by `phylo.opt` alone and lives in `opt/testfunctions.py`.

- **Frustration is what a triangle buys.** A two-state antiferromagnet wants
  every edge to disagree, which is possible exactly when the graph is
  2-colourable. Every lattice in `lattice_graph` is bipartite, so its
  antiferromagnetic ground state is unfrustrated and its energy is zero —
  which makes it useless as a hard case. `triangular_lattice_graph` adds one
  diagonal per cell, and on the periodic version a double count closes
  exactly: `3N` edges, `2N` triangles, each triangle needs an agreeing edge,
  each edge lies in two triangles, so at least `N` edges agree. Enumeration
  attains it at `N = 9, 12, 16`, so the ground-state energy is `|J| * N` at
  **any** size. That is the only claim in this repository that survives past
  enumeration without an approximation bound.

- **Wannier's constant is quoted and never asserted.** The residual entropy of
  0.3231 per site is a thermodynamic limit. Measured here it is 0.4153 at
  `N = 9`, 0.3516 at `N = 12` and 0.2336 at `N = 16` — not close, and not even
  monotone, because a `4x4` torus is incommensurate with the three-sublattice
  ground state. The exact degeneracies are asserted; the entropy is reported.
  Asserting a limit at a size where it does not hold is the mistake #214
  already made once with a graph threshold.

- **A planted state is a known energy, not a known optimum.** It upper bounds
  the ground-state energy at any size, which is the only oracle that survives
  past enumeration — and it is a strictly weaker claim than "the ground
  state". Measured at `n = 10` against enumeration, the planted state is the
  ground state in 60 of 60 instances at zero frustration, 41 at 0.1, 23 at
  0.2, 10 at 0.3 and 0 of 60 at 0.5.

- **Zero frustration is a relabelled ferromagnet.** With every coupling
  satisfying the planted state, the gauge `sigma_i = +/-1` read off that state
  turns every coupling positive, so any local search solves it. The parameter
  exists to be turned up, and a test pins the gauge equivalence so the trap is
  visible rather than folklore.

- **The planted spin glass does not replace #177, and that is measured.**
  Against 20-restart iterated conditional modes at `n = 100` and mean degree
  4, descent lands on the planted energy below frustration 0.2 (mean gap
  +0.30 to -0.25) and *beats* it above (-8.2 at 0.2, -25.7 at 0.3, so the
  planted state is no longer near-optimal there). Raising connectivity does
  not open a window: at mean degree 12 and frustration 0.05 descent matches
  the planted energy exactly on every instance. The fixture supplies a
  known-energy reference past enumeration; it is not a hard case, and the
  ticket's open question is answered in the negative rather than left open.

- **Two decoders, one HMM, and a fixture where they differ.** Viterbi
  maximizes a path; posterior decoding maximizes each site's marginal
  independently. They agree on almost every fixture, so a decoder that
  computes one and reports the other passes. `ambiguous_hmm` is built so they
  do not: Viterbi returns the constant path and posterior decoding returns the
  observations, which is the **5th** most likely path of 32 and 0.6066 nats
  behind. Both answers are checked to be non-degenerate — the Viterbi maximum
  is unique by 0.3033 nats and every marginal exceeds 0.6256 — because a
  symmetric first draft had a *three-way* tie at the maximum and the
  disagreement was an `argmax` artifact.
