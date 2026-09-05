"""Type stub for the compiled `phylo.oxiphylo` Rust extension.

Hand-written, so it can drift: keep the signatures here matching the
`#[pyfunction]` definitions in src/lib.rs, src/pruning.rs and
src/sampling.rs. Issue #37 tracks putting `stubtest` in CI so the drift is
caught by a check rather than by whoever notices; until then, `mypy --strict`
catches only the direction where the stub is missing something a caller
uses, which is how `sample_rows` was caught.
"""

import numpy as np

def double(x: int) -> int: ...
def pruning_log_likelihood(
    branch_length: list[float],
    children: list[list[int]],
    leaf_states: list[list[int]],
    k: int,
    pi: list[float],
    rescale: bool,
) -> float: ...
def sample_rows(
    distributions: np.ndarray,
    n_categories: int,
    rows: np.ndarray,
    draws: np.ndarray,
    out: np.ndarray,
) -> None: ...
