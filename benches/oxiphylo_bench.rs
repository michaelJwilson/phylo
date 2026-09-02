//! Criterion benchmarks for the `oxiphylo` bindings.
//!
//! `bench_double` is scaffolding, kept for the same demo binding
//! `src/lib.rs` still exposes. `bench_pruning_log_likelihood` measures the
//! real kernel (`src/pruning.rs`) at the same (taxa, site) sizes as
//! `tests/regression/fixtures/simulation_params*.yaml` -- 4 taxa / 200,000
//! sites and 8 taxa / 200,000 sites -- so this number is comparable to the
//! `pytest-benchmark` numbers in `tests/benchmarks/test_pruning_rust_bench.py`.
//! It calls `pruning_log_likelihood_impl` directly (the PyO3-free core, not
//! the `#[pyfunction]` wrapper) for the same link-time reason `cargo test`
//! does -- see `src/pruning.rs`'s module docs. CI runs `cargo bench` but
//! asserts nothing against the timings, since GitHub-hosted runner hardware
//! varies between runs. Compare locally with Criterion's `--save-baseline`
//! and `--baseline`.

use criterion::{criterion_group, criterion_main, Criterion};
use oxiphylo::double;
use oxiphylo::pruning::pruning_log_likelihood_impl;

fn bench_double(c: &mut Criterion) {
    c.bench_function("double", |b| b.iter(|| double(std::hint::black_box(21))));
}

/// A tiny deterministic PRNG (splitmix64) so the benchmark needs no `rand`
/// dependency -- only used to fill leaf states with realistic-looking data,
/// never for anything that must be reproducible science.
struct SplitMix64 {
    state: u64,
}

impl SplitMix64 {
    fn new(seed: u64) -> Self {
        Self { state: seed }
    }

    fn next_u64(&mut self) -> u64 {
        self.state = self.state.wrapping_add(0x9E3779B97F4A7C15);
        let mut z = self.state;
        z = (z ^ (z >> 30)).wrapping_mul(0xBF58476D1CE4E5B9);
        z = (z ^ (z >> 27)).wrapping_mul(0x94D049BB133111EB);
        z ^ (z >> 31)
    }

    fn next_state(&mut self, k: usize) -> i64 {
        (self.next_u64() % k as u64) as i64
    }
}

/// Build a balanced binary tree over `n_leaves` taxa (a power of two) with
/// `n_sites` random sites per leaf, in the post-order flat layout
/// `pruning_log_likelihood` expects: leaves first, each internal node after
/// both its children, root last.
fn build_balanced_tree(
    n_leaves: usize,
    n_sites: usize,
    k: usize,
    seed: u64,
) -> (Vec<f64>, Vec<Vec<usize>>, Vec<Vec<i64>>) {
    assert!(n_leaves.is_power_of_two());
    let mut rng = SplitMix64::new(seed);

    let mut branch_length = Vec::new();
    let mut children: Vec<Vec<usize>> = Vec::new();
    let mut leaf_states: Vec<Vec<i64>> = Vec::new();

    // level holds the flat-array index of each node at the current level,
    // starting with n_leaves leaves.
    let mut level: Vec<usize> = Vec::with_capacity(n_leaves);
    for _ in 0..n_leaves {
        let idx = branch_length.len();
        branch_length.push(0.05 + (rng.next_u64() % 1000) as f64 / 5000.0); // 0.05..0.25
        children.push(vec![]);
        leaf_states.push((0..n_sites).map(|_| rng.next_state(k)).collect());
        level.push(idx);
    }

    while level.len() > 1 {
        let mut next_level = Vec::with_capacity(level.len() / 2);
        for pair in level.chunks(2) {
            let idx = branch_length.len();
            let branch = if next_level.is_empty() && level.len() == 2 {
                0.0 // will be overwritten for the true root below
            } else {
                0.05 + (rng.next_u64() % 1000) as f64 / 5000.0
            };
            branch_length.push(branch);
            children.push(pair.to_vec());
            leaf_states.push(vec![]);
            next_level.push(idx);
        }
        level = next_level;
    }

    (branch_length, children, leaf_states)
}

fn bench_pruning_log_likelihood(c: &mut Criterion) {
    let k = 4usize;
    let pi = vec![0.25, 0.25, 0.25, 0.25];

    let mut group = c.benchmark_group("pruning_log_likelihood");
    for &(n_leaves, n_sites, label) in &[
        (4usize, 200_000usize, "4taxa_200000sites"),
        (8usize, 200_000usize, "8taxa_200000sites"),
    ] {
        let (branch_length, children, leaf_states) =
            build_balanced_tree(n_leaves, n_sites, k, 20260930);
        group.bench_function(label, |b| {
            b.iter(|| {
                pruning_log_likelihood_impl(
                    std::hint::black_box(&branch_length),
                    std::hint::black_box(&children),
                    std::hint::black_box(&leaf_states),
                    k,
                    &pi,
                    true,
                )
                .unwrap()
            })
        });
    }
    group.finish();
}

criterion_group!(benches, bench_double, bench_pruning_log_likelihood);
criterion_main!(benches);
