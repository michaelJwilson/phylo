"""Assemble per-change changelog fragments into ``CHANGELOG.md``.

A shared changelog file conflicts whenever two pull requests are merged
together, because both edit the same lines. A fragment per change removes the
conflict by construction: two pull requests never touch the same file, and git
has nothing to reconcile.

Each fragment lives in ``changelog.d/`` and is named ``<id>.<category>.md``,
where ``id`` is the pull-request number (or a slug, for work without one) and
``category`` is one of the Keep a Changelog headings. Its contents are the
entry text, without the leading bullet.

Run ``--check`` to validate fragment names, and ``--assemble`` at release to
fold them into the ``[Unreleased]`` section and delete them.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

#: Keep a Changelog headings, in the order they are rendered.
CATEGORIES: tuple[str, ...] = (
    "added",
    "changed",
    "deprecated",
    "removed",
    "fixed",
    "security",
)

FRAGMENT_NAME = re.compile(
    r"^(?P<id>[A-Za-z0-9][A-Za-z0-9_-]*)\.(?P<category>[a-z]+)\.md$"
)
UNRELEASED_HEADING = "## [Unreleased]"


def _sort_key(path: Path) -> tuple[int, int, str]:
    """Order fragments numerically where the id is a number, else by name."""
    match = FRAGMENT_NAME.match(path.name)
    identifier = match.group("id") if match else path.stem
    if identifier.isdigit():
        return (0, int(identifier), "")
    return (1, 0, identifier)


def find_fragments(directory: Path) -> list[Path]:
    """Return every markdown fragment in ``directory``, in render order."""
    if not directory.is_dir():
        return []
    found = [p for p in directory.iterdir() if p.is_file() and p.suffix == ".md"]
    return sorted((p for p in found if p.name != "README.md"), key=_sort_key)


def validate(directory: Path) -> list[str]:
    """Return one message per malformed fragment; empty means valid."""
    problems: list[str] = []
    for path in find_fragments(directory):
        match = FRAGMENT_NAME.match(path.name)
        if match is None:
            problems.append(
                f"{path.name}: expected <id>.<category>.md, "
                f"with category one of {', '.join(CATEGORIES)}"
            )
            continue
        category = match.group("category")
        if category not in CATEGORIES:
            problems.append(
                f"{path.name}: unknown category {category!r}; expected one of "
                f"{', '.join(CATEGORIES)}"
            )
        if not path.read_text(encoding="utf-8").strip():
            problems.append(f"{path.name}: empty, so it would render as a blank entry")
    return problems


def _as_bullet(text: str) -> list[str]:
    """Render fragment text as one markdown bullet, indenting continuations."""
    lines = [line.rstrip() for line in text.strip().splitlines()]
    bullet = [f"- {lines[0]}"]
    bullet.extend(f"  {line}" if line else "" for line in lines[1:])
    return bullet


def collect(directory: Path) -> dict[str, list[list[str]]]:
    """Group fragments by category, each rendered as bullet lines."""
    grouped: dict[str, list[list[str]]] = {}
    for path in find_fragments(directory):
        match = FRAGMENT_NAME.match(path.name)
        if match is None:
            continue
        category = match.group("category")
        grouped.setdefault(category, []).append(
            _as_bullet(path.read_text(encoding="utf-8"))
        )
    return grouped


def _split_unreleased(lines: list[str]) -> tuple[int, int]:
    """Return the line span of the ``[Unreleased]`` body, exclusive of headings."""
    try:
        start = lines.index(UNRELEASED_HEADING) + 1
    except ValueError as error:
        message = f"{UNRELEASED_HEADING} not found in the changelog"
        raise ValueError(message) from error
    end = len(lines)
    for offset, line in enumerate(lines[start:], start=start):
        if line.startswith("## "):
            end = offset
            break
    return start, end


def _parse_existing(body: list[str]) -> dict[str, list[list[str]]]:
    """Read the bullets already filed under each category heading."""
    grouped: dict[str, list[list[str]]] = {}
    category: str | None = None
    for line in body:
        if line.startswith("### "):
            category = line[4:].strip().lower()
            grouped.setdefault(category, [])
        elif category is not None and line.startswith("- "):
            grouped[category].append([line])
        elif category is not None and line.startswith("  ") and grouped.get(category):
            grouped[category][-1].append(line)
    return grouped


def _render(grouped: dict[str, list[list[str]]]) -> list[str]:
    """Render categories in canonical order, dropping empty ones."""
    rendered: list[str] = []
    for category in CATEGORIES:
        entries = grouped.get(category)
        if not entries:
            continue
        rendered.extend(["", f"### {category.capitalize()}", ""])
        for entry in entries:
            rendered.extend(entry)
    rendered.append("")
    return rendered


def assemble(directory: Path, changelog: Path, *, keep: bool = False) -> int:
    """Fold fragments into the changelog's Unreleased section.

    Returns the number of fragments folded in. Unless ``keep`` is set, the
    fragments are deleted, since their content now lives in the changelog.
    """
    problems = validate(directory)
    if problems:
        raise ValueError("; ".join(problems))

    fragments = find_fragments(directory)
    if not fragments:
        return 0

    lines = changelog.read_text(encoding="utf-8").splitlines()
    start, end = _split_unreleased(lines)

    grouped = _parse_existing(lines[start:end])
    for category, entries in collect(directory).items():
        grouped.setdefault(category, []).extend(entries)

    changelog.write_text(
        "\n".join([*lines[:start], *_render(grouped), *lines[end:]]) + "\n",
        encoding="utf-8",
    )
    if not keep:
        for path in fragments:
            path.unlink()
    return len(fragments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--directory", type=Path, default=Path("changelog.d"), help="fragment directory"
    )
    parser.add_argument(
        "--changelog", type=Path, default=Path("CHANGELOG.md"), help="changelog file"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="validate fragment names")
    mode.add_argument("--assemble", action="store_true", help="fold fragments in")
    parser.add_argument(
        "--keep", action="store_true", help="do not delete fragments after assembling"
    )
    args = parser.parse_args(argv)

    if args.check:
        problems = validate(args.directory)
        for problem in problems:
            print(f"changelog.d/{problem}", file=sys.stderr)
        return 1 if problems else 0

    folded = assemble(args.directory, args.changelog, keep=args.keep)
    print(f"folded {folded} fragment(s) into {args.changelog}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
