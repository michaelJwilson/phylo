use pyo3::prelude::*;

/// Example PyO3 binding: doubles an integer.
///
/// This is a placeholder demonstrating the Rust <-> Python binding pattern
/// for this crate. It is not a phylogenetics algorithm; real numerical
/// routines should replace/extend this once the Rust backend grows.
#[pyfunction]
pub fn double(x: i64) -> i64 {
    x * 2
}

/// `oxiphylo` is the compiled extension module imported from
/// `python/phylo/__init__.py` (see `pyproject.toml`'s `module-name`) as
/// `phylo.oxiphylo`.
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
