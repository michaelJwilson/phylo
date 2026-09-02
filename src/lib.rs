use pyo3::prelude::*;

pub mod pruning;

pub use pruning::pruning_log_likelihood;

/// Doubles an integer.
///
/// Placeholder binding: it demonstrates the Rust-to-Python pattern real
/// numerical kernels follow (`pruning::pruning_log_likelihood` is now the
/// substantive one) and implements no phylogenetics itself. Left in place
/// because `phylo.__init__` re-exports it and `tests/test_oxiphylo_bindings.py`
/// asserts it exists.
#[pyfunction]
pub fn double(x: i64) -> i64 {
    x * 2
}

/// The compiled extension module. `python/phylo/__init__.py` re-exports it as
/// `phylo.oxiphylo` (see `module-name` in `pyproject.toml`).
#[pymodule]
fn oxiphylo(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(double, m)?)?;
    m.add_function(wrap_pyfunction!(pruning_log_likelihood, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_double() {
        assert_eq!(double(21), 42);
        assert_eq!(double(0), 0);
        assert_eq!(double(-3), -6);
    }
}
