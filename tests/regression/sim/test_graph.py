"""Regression tests for `PottsGraph` and its N-D lattice constructor.

Node and edge counts are checked against closed-form combinatorics -- never
against the construction code under test (root `CLAUDE.md`, "Pin to
Independent Sources") -- across 1-D, 2-D and 3-D shapes and both boundary
conditions.
"""

from __future__ import annotations

from math import prod

import numpy as np
import pytest
from numpy.testing import assert_allclose
from phylo.sim.graph import BoundaryCondition, PottsGraph, is_open_chain, lattice_graph

# Shapes spanning 1-D, 2-D and 3-D, none with a degenerate (extent < 2)
# dimension so both boundary conditions apply to every one of them.
SHAPES = [(2,), (5,), (2, 3), (3, 4), (4, 4), (2, 3, 4), (3, 3, 3)]


@pytest.mark.parametrize("shape", SHAPES)
def test_node_count_is_the_shape_product(shape: tuple[int, ...]) -> None:
    graph = lattice_graph(shape, BoundaryCondition.OPEN, coupling=0.5)
    assert graph.n_nodes == prod(shape)


@pytest.mark.parametrize("shape", SHAPES)
def test_open_edge_count_matches_the_closed_form(shape: tuple[int, ...]) -> None:
    graph = lattice_graph(shape, BoundaryCondition.OPEN, coupling=0.5)
    expected = sum(
        (extent - 1) * prod(shape[:axis] + shape[axis + 1 :])
        for axis, extent in enumerate(shape)
    )
    assert len(graph.edges) == expected


@pytest.mark.parametrize("shape", SHAPES)
def test_periodic_edge_count_matches_the_closed_form(shape: tuple[int, ...]) -> None:
    graph = lattice_graph(shape, BoundaryCondition.PERIODIC, coupling=0.5)
    assert len(graph.edges) == len(shape) * prod(shape)


def test_a_1d_chain_is_the_n_equals_1_lattice() -> None:
    graph = lattice_graph((7,), BoundaryCondition.OPEN, coupling=1.0)
    assert graph.n_nodes == 7
    assert len(graph.edges) == 6
    assert graph.edges == tuple((i, i + 1) for i in range(6))
    assert is_open_chain(graph)


@pytest.mark.parametrize(
    "graph",
    [
        lattice_graph((7,), BoundaryCondition.PERIODIC, 1.0),
        lattice_graph((3, 3), BoundaryCondition.OPEN, 1.0),
        lattice_graph((3, 3), BoundaryCondition.PERIODIC, 1.0),
    ],
)
def test_only_an_open_1d_chain_dispatches_to_the_exact_sampler(
    graph: PottsGraph,
) -> None:
    assert not is_open_chain(graph)


def test_coupling_is_broadcast_to_every_edge() -> None:
    graph = lattice_graph((3, 3), BoundaryCondition.OPEN, coupling=1.25)
    assert_allclose(graph.coupling, 1.25)


def test_lattice_graph_rejects_an_empty_shape() -> None:
    with pytest.raises(ValueError, match="at least one dimension"):
        lattice_graph((), BoundaryCondition.OPEN, coupling=1.0)


def test_lattice_graph_rejects_a_sub_unit_extent() -> None:
    with pytest.raises(ValueError, match="every lattice extent must be >= 1"):
        lattice_graph((3, -1), BoundaryCondition.OPEN, coupling=1.0)


def test_periodic_boundary_rejects_a_degenerate_extent() -> None:
    with pytest.raises(ValueError, match="periodic boundary requires"):
        lattice_graph((1, 4), BoundaryCondition.PERIODIC, coupling=1.0)


def test_coupling_shape_must_match_the_edge_count() -> None:
    graph = lattice_graph((4,), BoundaryCondition.OPEN, coupling=1.0)
    with pytest.raises(ValueError, match="one entry per edge"):
        PottsGraph(
            n_nodes=graph.n_nodes,
            edges=graph.edges,
            coupling=graph.coupling[:-1],
            boundary=graph.boundary,
        )


def test_an_edge_may_not_reference_a_node_outside_the_graph() -> None:
    with pytest.raises(ValueError, match=r"outside \[0, 2\)"):
        PottsGraph(
            n_nodes=2,
            edges=((0, 2),),
            coupling=np.array([1.0]),
            boundary=BoundaryCondition.OPEN,
        )
