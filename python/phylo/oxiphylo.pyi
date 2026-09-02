"""Type stub for the compiled `phylo.oxiphylo` Rust extension.

Hand-written, so it can drift: keep the signatures here matching the
`#[pyfunction]` definitions in src/lib.rs and src/pruning.rs.
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
