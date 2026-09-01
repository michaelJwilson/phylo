//! Criterion benchmark for the `oxiphylo` Rust bindings.
//!
//! `double` is a placeholder binding, so this benchmark is placeholder
//! scaffolding too -- it exists to establish the pattern (Cargo.toml's
//! `[[bench]]` entry, `cargo bench`) for benchmarking real numerical
//! kernels once they replace it. Run locally with `cargo bench`; CI only
//! compile-checks this (`cargo bench --no-run`) since GitHub-hosted
//! runners' variable hardware makes CI timing numbers unreliable.

use criterion::{criterion_group, criterion_main, Criterion};
use oxiphylo::double;

fn bench_double(c: &mut Criterion) {
    c.bench_function("double", |b| b.iter(|| double(std::hint::black_box(21))));
}

criterion_group!(benches, bench_double);
criterion_main!(benches);
