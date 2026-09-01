"""Tests for the changelog fragment assembler.

The assembler exists to remove a class of merge conflict, so the properties
worth pinning are the ones that would reintroduce it or corrupt the changelog:
fragments must merge into the categories already present rather than appending
duplicate headings, categories must render in Keep a Changelog order, and
released sections below `[Unreleased]` must be left untouched.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from infra.changelog import assemble, validate

CHANGELOG = """\
# Changelog

## [Unreleased]

### Changed

- An entry that was already here.

## [0.1.0] - 2026-01-01

### Added

- The first release.
"""


def _write(directory: Path, name: str, text: str) -> None:
    (directory / name).write_text(text, encoding="utf-8")


def test_assemble_merges_into_existing_categories(tmp_path: Path) -> None:
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    _write(fragments, "12.changed.md", "A later change.\n")
    _write(fragments, "3.added.md", "An earlier addition.\n")
    _write(fragments, "7.fixed.md", "A fix.\n")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")

    folded = assemble(fragments, changelog)

    assert folded == 3
    assert (
        changelog.read_text(encoding="utf-8")
        == """\
# Changelog

## [Unreleased]

### Added

- An earlier addition.

### Changed

- An entry that was already here.
- A later change.

### Fixed

- A fix.

## [0.1.0] - 2026-01-01

### Added

- The first release.
"""
    )


def test_assemble_removes_fragments_and_leaves_none_behind(tmp_path: Path) -> None:
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    _write(fragments, "1.added.md", "Something.\n")
    _write(fragments, "README.md", "Not a fragment.\n")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")

    assemble(fragments, changelog)

    assert not (fragments / "1.added.md").exists()
    assert (fragments / "README.md").exists(), "the format guide is not a fragment"


def test_multi_line_fragments_indent_their_continuations(tmp_path: Path) -> None:
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    _write(fragments, "5.added.md", "First line.\nSecond line.\n")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")

    assemble(fragments, changelog)

    body = changelog.read_text(encoding="utf-8")
    assert "- First line.\n  Second line.\n" in body


def test_assembling_nothing_leaves_the_changelog_byte_identical(tmp_path: Path) -> None:
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")

    assert assemble(fragments, changelog) == 0
    assert changelog.read_text(encoding="utf-8") == CHANGELOG


def test_validate_rejects_unknown_categories_and_empty_entries(tmp_path: Path) -> None:
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    _write(fragments, "9.improved.md", "Not a Keep a Changelog category.\n")
    _write(fragments, "10.added.md", "   \n")

    problems = validate(fragments)

    assert len(problems) == 2
    assert any("improved" in problem for problem in problems)
    assert any("empty" in problem for problem in problems)


def test_assemble_refuses_a_changelog_without_an_unreleased_section(
    tmp_path: Path,
) -> None:
    fragments = tmp_path / "changelog.d"
    fragments.mkdir()
    _write(fragments, "1.added.md", "Something.\n")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# Changelog\n\n## [0.1.0] - 2026-01-01\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Unreleased"):
        assemble(fragments, changelog)
