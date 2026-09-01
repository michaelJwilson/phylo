"""Test for the run_phylo console-script placeholder.

See python/phylo/scripts/run_phylo.py -- this is a stub pending a real CLI;
this test just confirms it's wired up correctly (importable, runs, prints
something), matching pyproject.toml's [project.scripts] entry point.
"""

from __future__ import annotations

import pytest

from phylo.scripts.run_phylo import main


def test_main_runs_without_error(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    captured = capsys.readouterr()
    assert "phylo" in captured.out
