# likelihood/

Felsenstein pruning, and the dispatch that runs it on whatever hardware is
present. This is the hottest path in the project: every proposed move costs at
least one evaluation, and search proposes many.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

The pruning recursion, site- and subtree-level compression, the canonical
form used to key memoized results, and backends: a vectorized NumPy
reference, a differentiable PyTorch backend (`pruning_torch.py`, float64,
CPU), a non-differentiable Rust CPU backend (`pruning_rust.py`, wrapping
`oxiphylo.pruning_log_likelihood` from `src/pruning.rs`), landed; CUDA and
Metal/MPS dispatch belong here too but are not yet implemented (ROADMAP.md
Milestone 3).

`objective.py` adapts the recursion to `phylo.opt`'s fitting interface. It
lives here, not in `opt/`, because that package may import no application
module — the dependency runs application to infrastructure, never back.

## Local rules

- **The NumPy reference is the oracle and it stays.** Every accelerated
  backend is pinned against it. Deleting the slow path to "clean up" removes
  the only thing that says the fast path is right.
- **Correctness comes from brute force, not from another backend.** Direct
  marginalization over internal states at `n <= 6` is the test. Two backends
  agreeing proves nothing if both are wrong.
- **The pruning recursion is where the tolerance policy bites.** Root
  `CLAUDE.md` states it; here it means a backend is accepted when it agrees
  with the NumPy reference inside that tolerance, and rejected outside it —
  never adjusted until it matches.
- **Rescaling must stay differentiable.** Partial likelihoods underflow, so
  they are rescaled with the log of the scaling accumulated separately. That
  transformation sits inside the autodiff graph.
- **Memoize on the canonical form.** A topology has many Newick spellings;
  keying a cache on a raw string silently recomputes trees already scored.
- **Only the sum of the two root branches is estimable.** Under a reversible
  model the likelihood does not depend on where the root sits along the
  branch it subdivides, so on a rooted binary tree those two branches are
  confounded — measured at 3.6e-12 of log-likelihood across a 9:1 shift,
  against 14.7 for two non-root siblings. `objective.py` fits the pair as one
  parameter and reports their sum; halving it back is a drawing convention,
  never an estimate. A tree in the trifurcating-root convention has no such
  pair, which is why inference is normally done on unrooted topologies.
- **Differentiable backends keep branch lengths out of the topology.**
  `pruning_torch.py` takes branch lengths as a `torch.float64` tensor
  ordered by `branch_order(tau)`, separate from the `Node` tree; it never
  reads `Node.branch_length`, so `torch.autograd` differentiates only
  through the tensor, never through Python floats baked into the topology.
