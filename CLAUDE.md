# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Project

`phylo` is a high-performance scientific Python repository. Correctness and
reproducibility of numerical/scientific results take priority over
convenience.

## Environment

Use `uv` for environment and dependency management (Python 3.12):

```
uv venv --python 3.12
source .venv/bin/activate
```

## Conventions

- Prefer vectorized (NumPy/array-based) implementations over Python loops on
  hot paths; justify any deviation with a comment.
- Any change affecting numerical output must include or update a test that
  pins expected values (or tolerances).
- Keep dependencies minimal — new dependencies should be justified in the PR
  description.
- Do not silently change default parameters of scientific algorithms.

## Working with sub-agents

- When a task naturally splits into pieces that touch disjoint files (e.g. a
  Rust extension scaffold vs. a Python test harness), prefer parallel
  sub-agents, each in its own isolated git worktree, each opening its own
  PR. This keeps PRs small and independently reviewable and avoids merge
  conflicts between the pieces.
- When a task is coupled — it touches files another piece already owns, or
  its output depends on decisions made there (e.g. renaming the Rust
  extension, then wiring CI that has to know about both the Rust and Python
  halves) — do it sequentially in a single thread instead. Splitting coupled
  work across agents mostly adds cost (each agent re-derives context from
  scratch) without buying real parallelism, since the pieces still have to
  be reconciled by hand.

## Dependencies & external tools

- Any new dependency (Python package, Rust crate, GitHub Action, or other
  external tool) must be open source under an OSI-approved license. Do not
  add anything with a proprietary, unclear, or non-OSS license.
- Do not add a new external dependency or tool without the user's explicit
  permission first — ask before adding, don't add and explain afterward.
- When proposing a new dependency, check its popularity (GitHub stars,
  PyPI/crates.io download counts, or an equivalent adoption metric for its
  ecosystem) and flag it explicitly if it falls short of roughly 1,000
  GitHub stars (or a comparably low bar on its ecosystem's usual metric) —
  let the user decide whether a less-established tool is still the right
  call.
