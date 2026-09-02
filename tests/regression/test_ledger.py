"""Regression tests for the Aim run ledger.

``infra/CLAUDE.md`` requires every recorded run to carry enough to replay it.
These tests pin that rule from both sides: a complete manifest round-trips
through Aim unchanged, and an incomplete one is refused rather than recorded.
"""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pytest
from phylo.qa.ledger import (
    MANIFEST_VERSION,
    RunManifest,
    file_sha256,
    git_commit,
    hardware_description,
    read_runs,
    record_run,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

_DIGEST_A = "a" * 64
_DIGEST_B = "b" * 64


def _manifest(**overrides: object) -> RunManifest:
    """A complete manifest, with fields overridable per test."""
    fields: dict[str, object] = {
        "commit": "0123456789abcdef0123456789abcdef01234567",
        "uv_lock_sha256": _DIGEST_A,
        "cargo_lock_sha256": _DIGEST_B,
        "hardware": "Linux-x86_64-x86_64",
        "seed": 20260902,
        "dataset": "simulation_params.yaml",
        "model": "JC69(k=4)",
        "move_set": "none",
        "evaluation_budget": 0,
    }
    fields.update(overrides)
    return RunManifest(**fields)  # type: ignore[arg-type]


# --- the manifest rule: unreplayable runs are refused --------------------


@pytest.mark.parametrize(
    "field", ["commit", "hardware", "dataset", "model", "move_set"]
)
def test_manifest_rejects_an_empty_field(field: str) -> None:
    with pytest.raises(ValueError, match="anecdote"):
        _manifest(**{field: "   "})


@pytest.mark.parametrize("field", ["uv_lock_sha256", "cargo_lock_sha256"])
def test_manifest_rejects_a_lock_hash_that_is_not_a_digest(field: str) -> None:
    with pytest.raises(ValueError, match="not a sha256 hex digest"):
        _manifest(**{field: "not-a-digest"})


@pytest.mark.parametrize("field", ["uv_lock_sha256", "cargo_lock_sha256"])
def test_manifest_rejects_a_lock_hash_of_the_wrong_length(field: str) -> None:
    with pytest.raises(ValueError, match="not a sha256 hex digest"):
        _manifest(**{field: "abc123"})


def test_manifest_rejects_a_negative_budget() -> None:
    with pytest.raises(ValueError, match="evaluation_budget must be >= 0"):
        _manifest(evaluation_budget=-1)


def test_manifest_accepts_a_complete_specification() -> None:
    manifest = _manifest()
    assert manifest.seed == 20260902
    assert manifest.move_set == "none"


# --- environment derivation, checked against independent recomputation ---


def test_file_sha256_matches_an_independent_hash(tmp_path: Path) -> None:
    payload = b"lockfile contents\n"
    path = tmp_path / "uv.lock"
    path.write_bytes(payload)

    assert file_sha256(path) == hashlib.sha256(payload).hexdigest()


def test_git_commit_matches_rev_parse() -> None:
    expected = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    assert git_commit(REPO_ROOT) == expected


def test_git_commit_raises_outside_a_repository(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="cannot resolve HEAD"):
        git_commit(tmp_path)


def test_hardware_description_has_three_parts() -> None:
    assert len(hardware_description().split("-")) >= 3


def test_for_current_environment_derives_commit_and_lock_hashes() -> None:
    manifest = RunManifest.for_current_environment(
        REPO_ROOT, seed=7, dataset="fixture.yaml", model="JC69(k=4)"
    )

    assert manifest.commit == git_commit(REPO_ROOT)
    assert manifest.uv_lock_sha256 == file_sha256(REPO_ROOT / "uv.lock")
    assert manifest.cargo_lock_sha256 == file_sha256(REPO_ROOT / "Cargo.lock")
    # Not-applicable values are explicit, never silently absent.
    assert manifest.move_set == "none"
    assert manifest.evaluation_budget == 0


# --- the ledger itself ---------------------------------------------------


def test_recorded_run_round_trips_every_manifest_field(tmp_path: Path) -> None:
    pytest.importorskip("aim")
    manifest = _manifest()
    metrics = {"log_likelihood": -1234.5, "runtime_seconds": 4.25}

    run_hash = record_run(manifest, metrics, tmp_path / "ledger")
    (row,) = read_runs(tmp_path / "ledger")

    assert row["run_hash"] == run_hash
    assert row["manifest_version"] == MANIFEST_VERSION
    assert row["commit"] == manifest.commit
    assert row["uv_lock_sha256"] == manifest.uv_lock_sha256
    assert row["cargo_lock_sha256"] == manifest.cargo_lock_sha256
    assert row["hardware"] == manifest.hardware
    assert row["seed"] == manifest.seed
    assert row["dataset"] == manifest.dataset
    assert row["model"] == manifest.model
    assert row["move_set"] == manifest.move_set
    assert row["evaluation_budget"] == manifest.evaluation_budget
    assert row["metrics"] == pytest.approx(metrics)


def test_recorded_run_carries_no_system_metrics(tmp_path: Path) -> None:
    # System metrics vary run to run; a ledger row carrying them would not be
    # reproducible, so tracking is disabled.
    pytest.importorskip("aim")
    record_run(_manifest(), {"log_likelihood": -1.0}, tmp_path / "ledger")
    (row,) = read_runs(tmp_path / "ledger")

    assert not [name for name in row["metrics"] if name.startswith("__system__")]
    assert set(row["metrics"]) == {"log_likelihood"}


def test_ledger_accumulates_runs(tmp_path: Path) -> None:
    pytest.importorskip("aim")
    ledger = tmp_path / "ledger"
    first = record_run(_manifest(seed=1), {"log_likelihood": -10.0}, ledger)
    second = record_run(_manifest(seed=2), {"log_likelihood": -20.0}, ledger)

    rows = read_runs(ledger)
    assert {row["run_hash"] for row in rows} == {first, second}
    assert {row["seed"] for row in rows} == {1, 2}


def test_record_run_rejects_empty_metrics(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="measures nothing"):
        record_run(_manifest(), {}, tmp_path / "ledger")
