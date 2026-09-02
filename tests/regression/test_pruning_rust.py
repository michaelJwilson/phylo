"""Regression tests for ``phylo.likelihood.pruning_rust`` (the Rust CPU backend).

Checks per ``likelihood/CLAUDE.md``, mirroring ``test_pruning_torch.py``'s
structure for the PyTorch backend:

- Agreement with ``pruning.py``, the NumPy oracle every backend is pinned
  against (``test_rust_matches_numpy_oracle``).
- Agreement with ``brute_force.py`` at ``n <= 6`` taxa
  (``test_rust_matches_brute_force``) -- "correctness comes from brute
  force, not from another backend."
- Rescaled and unrescaled Rust paths agreeing
  (``test_rescaled_and_unrescaled_rust_paths_agree``).
- Validation-error parity with the NumPy oracle for malformed inputs,
  mirroring ``test_likelihood_validation.py``'s split for the pure-Python
  backends.

Requires the compiled extension (``maturin develop`` / ``pip install .``),
like ``tests/test_oxiphylo_bindings.py``.
"""

from __future__ import annotations

import numpy as np
import pytest
from numpy.testing import assert_allclose
from phylo.likelihood import pruning, pruning_rust
from phylo.likelihood.brute_force import brute_force_log_likelihood
from phylo.sim.simulate import simulate_alignment
from phylo.sim.tree import Node

# Same bound docs/tex/main.tex states for pruning_torch.py's agreement with
# the NumPy oracle ("Differentiable backends"): never relaxed to accommodate
# a discrepancy.
_ATOL_ORACLE = 1e-9


def _small_tree_n4() -> Node:
    """4-taxon tree with a trifurcating root, mirroring the pruning fixtures."""
    return Node(
        name="root",
        branch_length=None,
        children=(
            Node(name="A", branch_length=0.10),
            Node(name="B", branch_length=0.25),
            Node(
                name="ancestor_CD",
                branch_length=0.05,
                children=(
                    Node(name="C", branch_length=0.15),
                    Node(name="D", branch_length=0.40),
                ),
            ),
        ),
    )


def _small_tree_n6() -> Node:
    """6-taxon, fully binary tree."""
    return Node(
        name="root",
        branch_length=None,
        children=(
            Node(
                name="left",
                branch_length=0.08,
                children=(
                    Node(name="A", branch_length=0.10),
                    Node(name="B", branch_length=0.20),
                ),
            ),
            Node(
                name="right",
                branch_length=0.12,
                children=(
                    Node(
                        name="ancestor_CD",
                        branch_length=0.05,
                        children=(
                            Node(name="C", branch_length=0.15),
                            Node(name="D", branch_length=0.25),
                        ),
                    ),
                    Node(
                        name="ancestor_EF",
                        branch_length=0.05,
                        children=(
                            Node(name="E", branch_length=0.30),
                            Node(name="F", branch_length=0.10),
                        ),
                    ),
                ),
            ),
        ),
    )


def test_rust_matches_numpy_oracle() -> None:
    tau = _small_tree_n4()
    k = 4
    pi = np.full(k, 0.25)
    dataset = simulate_alignment(tau=tau, k=k, pi=pi, seed=20260920, n_sites=50)

    numpy_ll = pruning.log_likelihood(tau, k, pi, dataset.alignment)
    rust_ll = pruning_rust.log_likelihood(tau, k, pi, dataset.alignment)

    assert_allclose(rust_ll, numpy_ll, atol=_ATOL_ORACLE)


def test_rust_matches_brute_force() -> None:
    tau = _small_tree_n6()
    k = 4
    pi = np.full(k, 0.25)
    dataset = simulate_alignment(tau=tau, k=k, pi=pi, seed=20260921, n_sites=15)

    rust_ll = pruning_rust.log_likelihood(tau, k, pi, dataset.alignment)
    brute = brute_force_log_likelihood(tau, k, pi, dataset.alignment)

    assert_allclose(rust_ll, brute, atol=_ATOL_ORACLE)


def test_rescaled_and_unrescaled_rust_paths_agree() -> None:
    tau = _small_tree_n6()
    k = 4
    pi = np.full(k, 0.25)
    dataset = simulate_alignment(tau=tau, k=k, pi=pi, seed=20260922, n_sites=100)

    rescaled = pruning_rust.log_likelihood(tau, k, pi, dataset.alignment, rescale=True)
    unrescaled = pruning_rust.log_likelihood(
        tau, k, pi, dataset.alignment, rescale=False
    )

    assert_allclose(rescaled, unrescaled, rtol=1e-10)


def test_rust_rejects_mismatched_pi_shape() -> None:
    tau = Node(
        name="root",
        branch_length=None,
        children=(
            Node(name="A", branch_length=0.1),
            Node(name="B", branch_length=0.2),
        ),
    )
    alignment = {
        "A": np.zeros(5, dtype=np.int64),
        "B": np.zeros(5, dtype=np.int64),
    }
    with pytest.raises(ValueError, match="pi has shape"):
        pruning_rust.log_likelihood(tau, 4, np.full(3, 1.0 / 3), alignment)


def test_rust_rejects_alignment_missing_a_leaf() -> None:
    tau = Node(
        name="root",
        branch_length=None,
        children=(
            Node(name="A", branch_length=0.1),
            Node(name="B", branch_length=0.2),
        ),
    )
    alignment = {"A": np.zeros(5, dtype=np.int64)}
    with pytest.raises(ValueError, match="alignment is missing leaf"):
        pruning_rust.log_likelihood(tau, 4, np.full(4, 0.25), alignment)


def test_rust_rejects_non_root_node_without_branch_length() -> None:
    tau = Node(
        name="root",
        branch_length=None,
        children=(
            Node(name="A", branch_length=None),
            Node(name="B", branch_length=0.2),
        ),
    )
    alignment = {
        "A": np.zeros(5, dtype=np.int64),
        "B": np.zeros(5, dtype=np.int64),
    }
    with pytest.raises(ValueError, match="has no branch_length"):
        pruning_rust.log_likelihood(tau, 4, np.full(4, 0.25), alignment)
