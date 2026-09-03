"""Every module `CLAUDE.md` points at the writing style, and none restates it.

Root `CLAUDE.md` states that its **Writing Style** rules bind every module
file. Nothing enforced that: the eight module files carried a generic "these
are local" line that never named the section, so an agent reading one of them
alone had no way to know (issue #155).

Stating an invariant is not enforcing it. `docs/source/index.rst` claimed to
cover every submodule while missing all eighteen of `phylo.qa`, because
`sphinx-build -W` fails on a broken entry and never on an absent one (issue
#154). This module is the check that was missing there.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

# The directories root `CLAUDE.md` names as carrying their own file.
MODULE_DIRECTORIES = (
    "python/phylo/sim",
    "python/phylo/likelihood",
    "python/phylo/opt",
    "python/phylo/learn",
    "python/phylo/search",
    "python/phylo/qa",
    "infra",
    "docs",
)

POINTER = "**Writing Style**"

# Rule 5's label, distinctive enough that a file reproducing the section would
# contain it and a file referencing the section would not.
RESTATEMENT = "Apply naming, terminology, and syntax consistently"


def _module_claude_files() -> list[Path]:
    """Find every module `CLAUDE.md` on disk.

    Discovered rather than listed, so a module directory added without a
    `CLAUDE.md` is caught by the emptiness check below rather than passing
    because nobody updated a hardcoded list.

    Returns
    -------
    list[Path]
        Every `CLAUDE.md` under a package or tooling directory, sorted.
    """
    found = sorted(REPO_ROOT.glob("python/phylo/*/CLAUDE.md"))
    for directory in ("infra", "docs"):
        candidate = REPO_ROOT / directory / "CLAUDE.md"
        if candidate.is_file():
            found.append(candidate)
    return found


def test_every_named_module_directory_has_a_claude_md() -> None:
    # Root `CLAUDE.md` names these eight; a missing file would mean the rules
    # reach a module through nothing at all.
    missing = [
        directory
        for directory in MODULE_DIRECTORIES
        if not (REPO_ROOT / directory / "CLAUDE.md").is_file()
    ]

    assert missing == []


def test_every_module_claude_md_points_at_the_writing_style() -> None:
    # The ticket's substance: reading one module file must tell you the
    # writing style governs what you are about to write.
    silent = [
        str(path.relative_to(REPO_ROOT))
        for path in _module_claude_files()
        if POINTER not in path.read_text()
    ]

    assert silent == []


def test_no_module_claude_md_restates_the_writing_style() -> None:
    # The other half, and the reason the pointer is a pointer. Root
    # `CLAUDE.md`'s Writing Style section changed three times on the day this
    # was written; nine copies of it would already disagree.
    restating = [
        str(path.relative_to(REPO_ROOT))
        for path in _module_claude_files()
        if RESTATEMENT in path.read_text()
    ]

    assert restating == []


def test_a_module_directory_added_without_a_pointer_is_caught(
    tmp_path: Path,
) -> None:
    # The check itself, exercised: the assertion above passes vacuously if the
    # search finds nothing, so this pins that a file lacking the pointer is
    # actually detected rather than skipped.
    without = tmp_path / "CLAUDE.md"
    without.write_text("# newmodule/\n\nRoot `CLAUDE.md` holds the rules.\n")
    with_pointer = tmp_path / "other_CLAUDE.md"
    with_pointer.write_text(f"# other/\n\nRoot `CLAUDE.md`'s {POINTER} binds this.\n")

    assert POINTER not in without.read_text()
    assert POINTER in with_pointer.read_text()


def test_the_root_file_states_that_the_rules_reach_the_module_files() -> None:
    # The pointers are only true because root says so. If that sentence goes,
    # eight files start referring to a scope nothing declares.
    text = ROOT_CLAUDE_MD.read_text()

    assert "## Writing Style" in text
    assert "each module's `CLAUDE.md` included" in text


def test_the_expected_reader_contract_lives_only_in_docs() -> None:
    # It is a contract about the technical document, so the seven other module
    # files have no business restating it -- which is what issue #141 removed
    # from `docs/CLAUDE.md` in the other direction, and why only `docs/` may
    # refer to it.
    elsewhere = [
        str(path.relative_to(REPO_ROOT))
        for path in _module_claude_files()
        if "Expected Reader" in path.read_text() and path.parent.name != "docs"
    ]

    assert elsewhere == []
