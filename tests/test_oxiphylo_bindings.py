"""Integration test for the compiled Rust extension.

Requires the package to be built and installed (`pip install .`), unlike the
pure-Python tests under tests/regression and tests/benchmarks.
"""

from phylo.oxiphylo import double


def test_double() -> None:
    assert double(21) == 42
    assert double(0) == 0
    assert double(-3) == -6
