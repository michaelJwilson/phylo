use pyo3::prelude::*;

/// Doubles an integer.
///
/// Placeholder binding: it demonstrates the Rust-to-Python pattern that real
/// numerical kernels will follow, and implements no phylogenetics itself.
#[pyfunction]
pub fn double(x: i64) -> i64 {
    x * 2
}

/// The compiled extension module. `python/phylo/__init__.py` re-exports it as
/// `phylo.oxiphylo` (see `module-name` in `pyproject.toml`).
#[pymodule]
fn oxiphylo(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(double, m)?)?;
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
