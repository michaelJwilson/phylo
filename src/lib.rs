use pyo3::prelude::*;

/// Example PyO3 binding: doubles an integer.
///
/// This is a placeholder demonstrating the Rust <-> Python binding pattern
/// for this crate. It is not a phylogenetics algorithm; real numerical
/// routines should replace/extend this once the Rust backend grows.
#[pyfunction]
fn double(x: i64) -> i64 {
    x * 2
}

/// `_phylo` is the compiled extension module imported from
/// `python/phylo/__init__.py` (see `pyproject.toml`'s `module-name`).
#[pymodule]
fn _phylo(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(double, m)?)?;
    Ok(())
}
