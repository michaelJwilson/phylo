"""Type stub for the compiled `phylo.oxiphylo` Rust extension.

Hand-written, so it can drift: keep the signatures here matching the
`#[pyfunction]` definitions in src/lib.rs, src/pruning.rs and
src/maxflow.rs. Issue #37 tracks putting `stubtest` in CI; until it lands,
`mypy --strict` catches a signature that no longer type-checks at a call
site but not one that drifted without breaking one.
"""

def double(x: int) -> int: ...
def pruning_log_likelihood(
    branch_length: list[float],
    children: list[list[int]],
    leaf_states: list[list[int]],
    k: int,
    pi: list[float],
    rescale: bool,
) -> float: ...
def max_flow(
    n_nodes: int,
    arcs: list[int],
    capacity: list[float],
    source: int,
    sink: int,
) -> float: ...
def ising_ground_state(
    n_nodes: int,
    field: list[float],
    edges: list[int],
    coupling: list[float],
) -> list[int]: ...
