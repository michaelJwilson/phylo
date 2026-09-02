# sim/

Generates alignments from a known model (e.g. evolutionary) according to a well
defined truth fully defined in a yaml.  Scientific validation is provided by test
according to the known true parameters and expected properties.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

Simulation of `k`-state, e.g. 4, characters down a binary tree under a rate matrix `Q`,
branch lengths `t`, and a root distribution `π`: the `k`-state Jukes–Cantor
model first, then other models after.

`newick.py` is the package's single source of Newick functionality (root
`CLAUDE.md`, "Package Surface"): serializing a tree (optionally with
per-node ancestral states) to Newick, validating a Newick string against
the rooted-binary-tree grammar, and counting distinct topologies for a
given taxon count. `tree.py` holds only the `Node` structure and
traversals; nothing outside `newick.py` builds or parses Newick strings.

## Local rules

- **Validate against the analytic result, never against our own likelihood.**
  The technical document gives the closed form for `k`-state Jukes–Cantor
  transition probabilities.
- **Validation tests state their tolerance and run for a variety of site/taxa sizes according to 
goal: validation of benchmarking.**
