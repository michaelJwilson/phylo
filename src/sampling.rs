//! Vectorized inverse-CDF categorical sampling, ported from
//! `python/phylo/numerics.py` (the NumPy oracle) to Rust, exposed to Python
//! via PyO3 as `phylo.oxiphylo.sample_rows`.
//!
//! Issue #181's audit found this is 94-96% of `simulate_alignment`'s self
//! time at both a CI-sized and a larger fixture, and the only candidate in
//! that audit both genuinely hot end-to-end and CPU-bound with no autodiff
//! dependency. It is the `oxiphylo` case rather than the GPU one: the
//! function is called once per tree edge -- 3 to 70 times per simulation --
//! each call vectorized over sites, so there is too little work per call to
//! amortize a GPU launch (`CLAUDE.md`, Performance).
//!
//! **The uniforms are drawn in Python and passed in.** This module does no
//! sampling of its own and holds no generator. `phylo.sim`'s reproducibility
//! contract is that a seeded `numpy.random.Generator` determines the result,
//! and a second stream inside Rust would break it silently -- the same
//! reasoning `phylo.learn.policy.LinearPolicy.sample` gives for taking an
//! `rng` rather than reaching for torch's global generator. It also makes
//! bit-exactness against the oracle a property of the arithmetic alone,
//! which is what lets the regression test assert equality rather than a
//! tolerance.
//!
//! **Where the speedup comes from.** The oracle materializes
//! `cumulative[rows]`, an `(n_draws, n_categories)` array, then compares and
//! takes an `argmax` over it. This walks each row's cumulative distribution
//! in place and stops at the first crossing, so nothing of that size is
//! allocated and most draws exit after a couple of comparisons.
//!
//! The implementation (`sample_rows_impl`) is plain Rust with no PyO3 types
//! so `cargo test` can link it, per `src/pruning.rs`'s module docs.

use pyo3::buffer::PyBuffer;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

/// Draw one category per entry of `rows`, by inverse CDF.
///
/// # Parameters
/// - `distributions`: row-major `n_rows * n_categories`, each row summing to
///   1 within rounding.
/// - `n_categories`: row width; `distributions.len()` must be a multiple.
/// - `rows`: which row each draw comes from, entries in `[0, n_rows)`.
/// - `draws`: one uniform in `[0, 1)` per entry of `rows`, same length.
///
/// # Returns
/// The sampled category per entry, or `Err` describing the first violated
/// precondition.
pub fn sample_rows_impl(
    distributions: &[f64],
    n_categories: usize,
    rows: &[i64],
    draws: &[f64],
) -> Result<Vec<i64>, String> {
    if n_categories == 0 {
        return Err("n_categories must be positive".to_string());
    }
    if !distributions.len().is_multiple_of(n_categories) {
        return Err(format!(
            "distributions has {} entries, not a multiple of n_categories {}",
            distributions.len(),
            n_categories
        ));
    }
    if rows.len() != draws.len() {
        return Err(format!(
            "rows has {} entries and draws has {}; one draw per row is required",
            rows.len(),
            draws.len()
        ));
    }
    let n_rows = distributions.len() / n_categories;

    // Accumulate left to right, exactly as `np.cumsum(axis=1)` does, so the
    // partial sums are bit-identical to the oracle's; a pairwise or blocked
    // summation would be more accurate and would not match.
    let mut cumulative = vec![0.0_f64; distributions.len()];
    for row in 0..n_rows {
        let base = row * n_categories;
        let mut total = 0.0_f64;
        for column in 0..n_categories {
            total += distributions[base + column];
            cumulative[base + column] = total;
        }
        // The clamp the oracle's docstring calls out: a row summing to
        // `1 - 4e-16` leaves a sliver of the unit interval above its own
        // total, and a draw landing there is past every column.
        cumulative[base + n_categories - 1] = 1.0;
    }

    let mut sampled = Vec::with_capacity(rows.len());
    for (index, &row) in rows.iter().enumerate() {
        if row < 0 || row as usize >= n_rows {
            return Err(format!(
                "rows[{}] is {}, outside [0, {})",
                index, row, n_rows
            ));
        }
        let base = row as usize * n_categories;
        let draw = draws[index];
        // `np.argmax` over an all-false row returns 0, and this matches it.
        // The clamp above makes that unreachable for a draw in [0, 1), but
        // matching the oracle where it cannot be observed is cheaper than
        // arguing that it cannot.
        let mut chosen = 0_i64;
        for column in 0..n_categories {
            if draw < cumulative[base + column] {
                chosen = column as i64;
                break;
            }
        }
        sampled.push(chosen);
    }
    Ok(sampled)
}

/// PyO3 wrapper over [`sample_rows_impl`]; converts `Err` to `ValueError`.
///
/// **Arrays cross the boundary through the buffer protocol, and the result is
/// written into a caller-allocated one.** The obvious binding -- `Vec<f64>`
/// in, `Vec<i64>` out -- makes PyO3 build a Python list per argument and per
/// result, and at two million draws that marshalling costs 64 ms in and
/// 125 ms back against a NumPy oracle that finishes the whole job in 86 ms.
/// A kernel three times faster than the thing it replaces still loses if the
/// boundary is priced in objects. `PyBuffer` moves the same data as a
/// contiguous copy and no Python objects at all.
///
/// `out` is a writable, C-contiguous `int64` buffer of the same length as
/// `rows`; the caller allocates it (`numpy.empty`) so that the result never
/// becomes a list on either side.
#[pyfunction]
#[pyo3(signature = (distributions, n_categories, rows, draws, out))]
pub fn sample_rows(
    py: Python<'_>,
    distributions: PyBuffer<f64>,
    n_categories: usize,
    rows: PyBuffer<i64>,
    draws: PyBuffer<f64>,
    out: PyBuffer<i64>,
) -> PyResult<()> {
    let distributions = distributions.to_vec(py)?;
    let rows = rows.to_vec(py)?;
    let draws = draws.to_vec(py)?;
    let sampled = sample_rows_impl(&distributions, n_categories, &rows, &draws)
        .map_err(PyValueError::new_err)?;
    out.copy_from_slice(py, &sampled)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_a_draw_below_the_first_boundary_takes_the_first_category() {
        let distributions = vec![0.25, 0.25, 0.5];
        let sampled = sample_rows_impl(&distributions, 3, &[0, 0, 0], &[0.0, 0.3, 0.6]).unwrap();
        assert_eq!(sampled, vec![0, 1, 2]);
    }

    #[test]
    fn test_the_last_column_is_clamped_to_one() {
        // Sums to just under 1, so without the clamp a draw in the sliver
        // above the total crosses no column.
        let distributions = vec![0.5, 0.5 - 4e-16];
        let sampled = sample_rows_impl(&distributions, 2, &[0], &[1.0 - f64::EPSILON]).unwrap();
        assert_eq!(sampled, vec![1]);
    }

    #[test]
    fn test_rows_select_among_distributions() {
        let distributions = vec![1.0, 0.0, 0.0, 1.0];
        let sampled = sample_rows_impl(&distributions, 2, &[0, 1, 0, 1], &[0.5; 4]).unwrap();
        assert_eq!(sampled, vec![0, 1, 0, 1]);
    }

    #[test]
    fn test_a_row_outside_the_distribution_count_is_refused() {
        let error = sample_rows_impl(&[0.5, 0.5], 2, &[1], &[0.5]).unwrap_err();
        assert!(error.contains("outside [0, 1)"), "{error}");
    }

    #[test]
    fn test_mismatched_rows_and_draws_are_refused() {
        let error = sample_rows_impl(&[0.5, 0.5], 2, &[0, 0], &[0.5]).unwrap_err();
        assert!(error.contains("one draw per row"), "{error}");
    }

    #[test]
    fn test_a_ragged_distribution_array_is_refused() {
        let error = sample_rows_impl(&[0.5, 0.5, 0.5], 2, &[0], &[0.5]).unwrap_err();
        assert!(error.contains("not a multiple"), "{error}");
    }
}
