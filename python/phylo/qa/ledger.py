"""Ledger of benchmarked and validated runs, recorded with Aim.

``infra/CLAUDE.md`` fixes what a run must carry: the commit, the ``uv.lock``
and ``Cargo.lock`` hashes, the seed, the dataset identity, the model
specification, the move set, the evaluation budget, and the hardware -- "a run
that cannot be replayed from its manifest is an anecdote". :class:`RunManifest`
makes that rule executable: every field is required and an empty one raises,
so an unreplayable run cannot be recorded in the first place.

Aim is an optional dependency (the ``tracking`` extra). It is imported inside
the functions that need it, so importing this module -- and therefore
``phylo.qa`` -- costs nothing when tracking is not installed.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

# Recorded on every run so a reader can tell which manifest schema produced a
# row. Bump it when a field is added, renamed, or given a new meaning.
MANIFEST_VERSION = 1

_NOT_APPLICABLE = "none"


@dataclass(frozen=True)
class RunManifest:
    """Everything needed to replay a run, per ``infra/CLAUDE.md``.

    Parameters
    ----------
    commit : str
        Git commit the run was executed at.
    uv_lock_sha256 : str
        SHA-256 of ``uv.lock``, pinning the Python dependency graph.
    cargo_lock_sha256 : str
        SHA-256 of ``Cargo.lock``, pinning the Rust dependency graph.
    hardware : str
        Machine the run executed on, as ``system-machine-processor``.
    seed : int
        Seed passed to ``np.random.default_rng``.
    dataset : str
        Dataset identity -- a fixture name, not a description.
    model : str
        Model specification, e.g. ``"JC69(k=4)"``.
    move_set : str
        Move set searched over. ``"none"`` for a run that does no topological
        search, stated explicitly rather than defaulted.
    evaluation_budget : int
        Likelihood evaluations the run was allowed. ``0`` for a run with no
        budget, stated explicitly rather than defaulted.

    Raises
    ------
    ValueError
        If any string field is empty, if ``evaluation_budget`` is negative, or
        if either lockfile hash is not 64 hex characters.
    """

    commit: str
    uv_lock_sha256: str
    cargo_lock_sha256: str
    hardware: str
    seed: int
    dataset: str
    model: str
    move_set: str
    evaluation_budget: int

    def __post_init__(self) -> None:
        for name, value in asdict(self).items():
            if isinstance(value, str) and not value.strip():
                msg = f"{name} is empty; a run that cannot be replayed is an anecdote"
                raise ValueError(msg)

        for name in ("uv_lock_sha256", "cargo_lock_sha256"):
            digest = getattr(self, name)
            if len(digest) != 64 or not all(c in "0123456789abcdef" for c in digest):
                msg = f"{name} is not a sha256 hex digest: {digest!r}"
                raise ValueError(msg)

        if self.evaluation_budget < 0:
            msg = f"evaluation_budget must be >= 0, got {self.evaluation_budget}"
            raise ValueError(msg)

    @classmethod
    def for_current_environment(
        cls,
        repo_root: Path,
        *,
        seed: int,
        dataset: str,
        model: str,
        move_set: str = _NOT_APPLICABLE,
        evaluation_budget: int = 0,
    ) -> RunManifest:
        """Build a manifest, deriving the environment fields from ``repo_root``.

        Parameters
        ----------
        repo_root : Path
            Repository root, holding ``uv.lock`` and ``Cargo.lock``.
        seed : int
            Seed the run used.
        dataset : str
            Dataset identity.
        model : str
            Model specification.
        move_set : str
            Move set searched over; defaults to ``"none"``.
        evaluation_budget : int
            Evaluation budget; defaults to ``0``.

        Returns
        -------
        RunManifest
            Manifest with commit, lockfile hashes, and hardware filled in.
        """
        return cls(
            commit=git_commit(repo_root),
            uv_lock_sha256=file_sha256(repo_root / "uv.lock"),
            cargo_lock_sha256=file_sha256(repo_root / "Cargo.lock"),
            hardware=hardware_description(),
            seed=seed,
            dataset=dataset,
            model=model,
            move_set=move_set,
            evaluation_budget=evaluation_budget,
        )


def file_sha256(path: Path) -> str:
    """SHA-256 of a file, as a hex digest.

    Parameters
    ----------
    path : Path
        File to hash.

    Returns
    -------
    str
        64-character lowercase hex digest.
    """
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit(repo_root: Path) -> str:
    """Resolve ``repo_root``'s current commit.

    Parameters
    ----------
    repo_root : Path
        Repository to inspect.

    Returns
    -------
    str
        Full 40-character commit SHA.

    Raises
    ------
    RuntimeError
        If git cannot resolve HEAD -- recording a run against an unknown
        commit would produce an unreplayable row.
    """
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        msg = f"cannot resolve HEAD in {repo_root}"
        raise RuntimeError(msg) from exc
    return completed.stdout.strip()


def hardware_description() -> str:
    """Describe the current machine, for the manifest's ``hardware`` field.

    Returns
    -------
    str
        ``system-machine-processor``, e.g. ``Linux-x86_64-x86_64``.
    """
    processor = platform.processor() or "unknown"
    return f"{platform.system()}-{platform.machine()}-{processor}"


def record_run(
    manifest: RunManifest,
    metrics: Mapping[str, float],
    repo_path: Path,
    *,
    experiment: str = "phylo",
) -> str:
    """Record one validated run into the Aim repository at ``repo_path``.

    Parameters
    ----------
    manifest : RunManifest
        The run's replay manifest. Stored as run parameters.
    metrics : Mapping[str, float]
        Scalar metrics for this run, e.g. ``{"log_likelihood": -1234.5}``.
        Empty is rejected: a run recording nothing measures nothing.
    repo_path : Path
        Directory holding the Aim repository. Created if absent.
    experiment : str
        Aim experiment to file the run under.

    Returns
    -------
    str
        The Aim run hash, which identifies the row in the ledger.

    Raises
    ------
    ValueError
        If ``metrics`` is empty.

    Notes
    -----
    System metrics are disabled (``system_tracking_interval=None``): they vary
    run to run and would make a ledger row irreproducible. The run is indexed
    explicitly on close, because Aim leaves a closed-but-unindexed run
    invisible to ``Repo.iter_runs``.
    """
    if not metrics:
        msg = "metrics is empty; a run recording nothing measures nothing"
        raise ValueError(msg)

    from aim.sdk.run import Run

    repo_path.mkdir(parents=True, exist_ok=True)

    run = Run(
        repo=str(repo_path),
        experiment=experiment,
        system_tracking_interval=None,
    )
    run["manifest_version"] = MANIFEST_VERSION
    for field_name, value in asdict(manifest).items():
        run[field_name] = value
    for name, value in metrics.items():
        run.track(float(value), name=name, step=0)

    run_hash: str = run.hash
    run.close()

    _index(repo_path, run_hash)
    return run_hash


def read_runs(repo_path: Path) -> list[dict[str, Any]]:
    """Read every recorded run back out of the ledger.

    Parameters
    ----------
    repo_path : Path
        Directory holding the Aim repository.

    Returns
    -------
    list[dict[str, Any]]
        One dict per run: every manifest field, plus ``metrics`` mapping each
        metric name to its last recorded value, plus the Aim ``run_hash``.
    """
    from aim.sdk.repo import Repo

    repo = Repo.from_path(str(repo_path))

    rows: list[dict[str, Any]] = []
    for run in repo.iter_runs():
        row: dict[str, Any] = {"run_hash": run.hash}
        for field_name in _MANIFEST_FIELDS:
            row[field_name] = run[field_name]
        row["manifest_version"] = run["manifest_version"]
        # `last_value` is O(1). Materializing the sequence instead
        # (`list(metric.values)`, `.tolist()`) allocates across the whole
        # sparse index range and raises MemoryError.
        row["metrics"] = {
            metric.name: float(metric.values.last_value()) for metric in run.metrics()
        }
        rows.append(row)
    return rows


def _index(repo_path: Path, run_hash: str) -> None:
    """Index a closed run so ``Repo.iter_runs`` can see it."""
    from aim.sdk.index_manager import RepoIndexManager
    from aim.sdk.repo import Repo

    manager = RepoIndexManager.get_index_manager(Repo.from_path(str(repo_path)))
    manager.index(run_hash)


_MANIFEST_FIELDS = tuple(RunManifest.__dataclass_fields__)
