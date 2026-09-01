# likelihood/

Felsenstein pruning, and the dispatch that runs it on whatever hardware is
present. This is the hottest path in the project: every proposed move costs at
least one evaluation, and search proposes many.

Root `CLAUDE.md` holds the repository-wide rules. These are local.

## What lives here

The pruning recursion, site- and subtree-level compression, the canonical
form used to key memoized results, and backends: a vectorized NumPy
reference, an efficient CPU path, CUDA, and Metal/MPS.

## Local rules

- **The NumPy reference is the oracle and it stays.** Every accelerated
  backend is pinned against it. Deleting the slow path to "clean up" removes
  the only thing that says the fast path is right.
- **Correctness comes from brute force, not from another backend.** Direct
  marginalization over internal states at `n <= 6` is the test. Two backends
  agreeing proves nothing if both are wrong.
- **Cross-device agreement is a tolerance, not bitwise equality.** `float32`
  and `float64` behave differently across CPU, CUDA, and Metal, and a deep
  recursion accumulates that. The tolerance is stated once in the technical
  document; a discrepancy inside it is not a bug and must not be "fixed".
- **Rescaling must stay differentiable.** Partial likelihoods underflow, so
  they are rescaled with the log of the scaling accumulated separately. That
  transformation sits inside the autodiff graph.
- **Memoize on the canonical form.** A topology has many Newick spellings;
  keying a cache on a raw string silently recomputes trees already scored.
