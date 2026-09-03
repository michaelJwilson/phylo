"""Validation-error paths for `load_potts_lattice_params`.

Separated from `tests/regression/sim/test_potts.py`, which pins scientific
correctness, per the pattern `test_jc_validation.py` sets for the alignment
simulator's own loader.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from phylo.sim.potts import load_potts_lattice_params

from tests._fixtures import FIXTURES_DIR

FIXTURE = FIXTURES_DIR / "potts_lattice_params.yaml"


def test_a_missing_field_is_refused(tmp_path: Path) -> None:
    text = "\n".join(
        line
        for line in FIXTURE.read_text().splitlines()
        if not line.startswith("shape:")
    )
    path = tmp_path / "potts_lattice.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match="missing required field"):
        load_potts_lattice_params(path)


@pytest.mark.parametrize(
    ("replace", "with_", "message"),
    [
        ("n_states: 3", "n_states: 1", "n_states must be >= 2"),
        ("shape: [3, 3]", "shape: []", "at least one dimension"),
        ("boundary: open", "boundary: toroidal", "boundary must be one of"),
        ("field: [0.30, -0.10, -0.20]", "field: [0.3, -0.1]", "field has shape"),
        ("n_chains: 200", "n_chains: 0", "n_chains must be >= 1"),
        ("burn_in: 300", "burn_in: -1", "burn_in must be >= 0"),
        ("sweeps: 4", "sweeps: 0", "sweeps must be >= 1"),
        ("thin: 3", "thin: 0", "thin must be >= 1"),
    ],
)
def test_an_unusable_value_is_refused(
    replace: str, with_: str, message: str, tmp_path: Path
) -> None:
    path = tmp_path / "potts_lattice.yaml"
    path.write_text(FIXTURE.read_text().replace(replace, with_))
    with pytest.raises(ValueError, match=message):
        load_potts_lattice_params(path)
