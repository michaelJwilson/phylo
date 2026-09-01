# Changelog fragments

One file per change, folded into `CHANGELOG.md` at release. Two pull requests
never edit the same file, so the changelog cannot produce a merge conflict.

Name a fragment `<id>.<category>.md`:

- **id** — the pull-request number, or a short slug for work without one.
- **category** — `added`, `changed`, `deprecated`, `removed`, `fixed`, or
  `security`, matching Keep a Changelog.

The contents are the entry text, without a leading bullet. Multiple lines are
allowed; continuations are indented when rendered.

```
$ cat changelog.d/42.added.md
Simulation of k-state characters under a supplied rate matrix, seeded and
reproducible from its manifest.
```

Validate names with `python -m infra.changelog --check`. At release, fold
everything in and delete the fragments with `python -m infra.changelog
--assemble`.
