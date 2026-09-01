//! Criterion benchmarks for the `oxiphylo` bindings.
//!
//! `double` is a placeholder, so this benchmark is scaffolding: it fixes the
//! pattern (a `[[bench]]` entry in Cargo.toml, `cargo bench`) for real kernels
//! to follow. CI runs `cargo bench` but asserts nothing against the timings,
//! since GitHub-hosted runner hardware varies between runs. Compare locally
//! with Criterion's `--save-baseline` and `--baseline`.

use criterion::{criterion_group, criterion_main, Criterion};
use oxiphylo::double;

fn bench_double(c: &mut Criterion) {
    c.bench_function("double", |b| b.iter(|| double(std::hint::black_box(21))));
}

criterion_group!(benches, bench_double);
criterion_main!(benches);
