<!--
This template mirrors CLAUDE.md's "Definition of Done" and "Documentation
Sync" rules. Fill in every section; delete none of them.
-->

### Description

<!-- What changed, and why. Link the issue this closes, if any. -->

### Benchmark

<!--
Required whenever a hot function is new or changed (CLAUDE.md, Performance /
Definition of Done). Report baseline vs. new numbers from pytest-benchmark
or criterion. Write "N/A — no hot-path change" if this PR doesn't touch one.
-->

| Function | Baseline | This PR | Delta |
| --- | --- | --- | --- |
|  |  |  |  |

### Documentation Sync

<!--
CLAUDE.md requires updating, in this PR, whichever of these the change makes
untrue. Check the ones this PR updates, or check "None applicable".
-->

- [ ] `README.md`
- [ ] `CLAUDE.md` (root or a module's)
- [ ] `DEV.md`
- [ ] `INSTALL.md`
- [ ] `ROADMAP.md`
- [ ] `docs/tex/`
- [ ] `CHANGELOG.md` (`[Unreleased]`, if user-visible)
- [ ] `STATUS.md` (if this changes an item's status)
- [ ] None applicable

### Definition of Done

- [ ] **Regression test:** asserts scientific validity (not just shape/execution) and pins the expected output.
- [ ] **Benchmark:** new/changed hot functions include a `pytest-benchmark` (Python) or `criterion` (Rust) bench, with baseline numbers reported above.
- [ ] **Coverage:** the `--cov-fail-under` gate is maintained or raised.
- [ ] **Docs & tooling:** `ruff`, `mypy --strict`, and `cargo` checks pass locally; Documentation Sync above is satisfied.
- [ ] **Dependency hygiene:** new dependencies are OSI-licensed, justified above, and flagged if under 1,000 GitHub stars.
