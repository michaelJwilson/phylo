# changelog.d/

Fragments here are merged into `CHANGELOG.md` at release time by
[towncrier](https://towncrier.readthedocs.io); see `[tool.towncrier]` in
`pyproject.toml` for the configuration.

## Adding a fragment

Every user-visible change adds one file to this directory, named:

```
<issue-number>.<type>.md
```

`<issue-number>` is the GitHub issue or PR number the change belongs to.
`<type>` is one of, mapped onto this project's Keep a Changelog sections:

| Type       | Section    |
| ---------- | ---------- |
| `added`    | Added      |
| `changed`  | Changed    |
| `fixed`    | Fixed      |
| `removed`  | Removed    |
| `security` | Security   |

The file's content is the changelog entry itself, e.g. `changelog.d/61.added.md`:

```markdown
Adopted towncrier to manage CHANGELOG.md via fragments.
```

CI's `towncrier check` fails a PR that changes user-visible behavior without
a matching fragment. A PR that touches only infrastructure, tests, or docs
needs none.

## Building the changelog

Fragments accumulate unrendered until a release. `towncrier build` then
consumes every fragment, deletes them, and inserts a new dated `## [version]`
section into `CHANGELOG.md` — this is a release step, not something a
feature PR runs.
