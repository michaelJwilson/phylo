# likelihood/

Felsenstein pruning, and the dispatch that runs it on whatever hardware is
present. This is the hottest path in the project: every proposed move costs at
least one evaluation, and search proposes many.

Root `CLAUDE.md` holds the repository-wide rules, and its **Writing Style**
section binds this file too — and every docstring, comment and commit message
in this module. It is referenced here, never restated. What follows is local.

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

`potts.py` and `belief_propagation.py` are the Potts MRF's evaluators:
exhaustive enumeration and the 2-D strip transfer matrix as exact oracles, and
sum-product belief propagation as the approximate one they referee.

`hmm_paths.py` enumerates every hidden path of an HMM, on the same footing as
`brute_force.py` does for a tree: exponential, sharing no recursion with the
forward algorithm in `phylo.opt.hmm`, and therefore able to referee it. Its
job is not evidence — the forward recursion computes that faster and they are
pinned against each other — but to hold *both* decodings of one sequence at
once, so Viterbi and posterior decoding can be separated by a fixture rather
than by assertion.

## Local rules

- **The NumPy reference is the oracle and it stays.** Every accelerated
  backend is pinned against it. Deleting the slow path to "clean up" removes
  the only thing that says the fast path is right.
- **Correctness comes from brute force, not from another backend.** Direct
  marginalization over internal states at `n <= 6` is the test. Two backends
  agreeing proves nothing if both are wrong.
- **The cross-device tolerance lives here, with its evidence.** Backends run
  on different hardware in different precisions, so agreement is a tolerance,
  never bitwise equality. Two numbers, stated in `device.py` and used from
  there rather than retyped: `1e-11` relative where both sides are `float64`,
  `1e-6` where either side is `float32`. PyTorch's Metal backend rejects
  `float64`, so every Apple Silicon comparison is a `float32` one, and a
  single bound loose enough to admit those would let a broken `float64`
  backend pass — hence keying on the lowest precision taking part.

  Both are **relative**, and that is forced rather than preferred. The total
  log-likelihood is a sum over sites, so its magnitude and any absolute
  discrepancy in it grow with the site count. Measuring `float32` against
  `float64` on the regression fixtures:

  | taxa, sites | \|lnL\| | absolute | relative |
  | --- | --- | --- | --- |
  | 4, 20 000 | 8.1e+04 | 4.38e-03 | 5.38e-08 |
  | 4, 200 000 | 8.2e+05 | 3.61e-02 | 4.41e-08 |
  | 8, 200 000 | 1.5e+06 | 4.99e-02 | 3.36e-08 |

  The absolute column spans an order of magnitude while the relative column
  is flat at roughly 0.4 times `float32` epsilon, which is the floor. An
  absolute bound fixed at one problem size does not transfer to another. And
  near `|lnL| = 2.4e5` adjacent `float32` values are `0.0156` apart, so no
  absolute bound tighter than that is achievable in `float32` at all,
  however good the kernel. Both tolerances sit better than an order of
  magnitude above the measured agreement, leaving room for a device that
  reorders reductions differently from the CPU.
- **The pruning recursion is where the tolerance policy bites.** Root
  `CLAUDE.md` states it; here it means a backend is accepted when it agrees
  with the NumPy reference inside that tolerance, and rejected outside it —
  never adjusted until it matches.
- **An approximate evaluator states which regime carries its correctness.**
  Belief propagation is exact on a tree and approximate on a loop, so the two
  regimes get different kinds of test and conflating them would prove nothing.
  Equality against enumeration is asserted on the tree; on the lattice the
  deviation from the strip transfer matrix is *reported*, because asserting
  agreement would assert something false and asserting only that it ran is the
  coverage theatre root `CLAUDE.md` forbids. What is asserted on the lattice
  is structure the physics fixes independently: exact at zero coupling, and a
  deviation peaking near `J_c = ln(1 + sqrt(q))` rather than growing without
  bound.

- **Refuse rather than return an unconverged number.** A Bethe free energy
  read off messages that never settled is not an estimate of anything, and a
  caller cannot distinguish it from one that is. `belief_propagation` raises
  `ConvergenceError` carrying the residual it stopped at. The same reasoning
  rejects `damping = 1`, where no message ever updates and every graph would
  report convergence on the first sweep with the residual identically zero.

- **The oracle for a loopy lattice cannot be enumeration alone.** Enumeration
  is exponential in the site count and stops at about nine sites; the strip
  transfer matrix is exponential in the *width* only, so it reaches a 6x4
  lattice that BP finds hard. It is itself pinned twice — against enumeration
  where both fit, and by reduction, since a strip of width 1 is a chain and
  must reproduce `phylo.opt.potts.log_partition` to machine precision.

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

- **Viterbi and posterior decoding are different answers, not approximations
  of each other.** One maximizes a path; the other maximizes each site's
  marginal independently, and the sequence it returns need not be a path the
  model favours — on `phylo.sim.canonical.ambiguous_hmm` it is the 5th most
  likely of 32. They agree on almost every fixture, which is exactly why a
  decoder that computes one and reports the other survives a suite that never
  builds a case where they diverge. `hmm_paths.py` reads both off one
  enumeration, so neither is trusted to validate the other.
