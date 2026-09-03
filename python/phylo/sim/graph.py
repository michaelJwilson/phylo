"""General undirected graphs for Markov random fields, and N-D lattice constructors.

``PottsGraph`` is the one representation a Potts model is defined over
(issue #170): nodes, a per-edge coupling ``J_ij``, and the boundary condition
the graph was built under. An N-D lattice is a constructed case of it rather
than a second type -- ``lattice_graph`` returns a ``PottsGraph``, and a 1-D
chain is ``lattice_graph((L,), ...)``, the ``N = 1`` case. ``phylo.sim.potts``
samples the model this module only describes; nothing here draws a spin.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from itertools import product

import numpy as np


class BoundaryCondition(Enum):
    """How a lattice's outermost sites are connected."""

    OPEN = "open"
    PERIODIC = "periodic"


@dataclass(frozen=True)
class PottsGraph:
    """An undirected graph carrying one Potts coupling per edge.

    Parameters
    ----------
    n_nodes : int
        Number of nodes, indexed ``0 .. n_nodes - 1``.
    edges : tuple[tuple[int, int], ...]
        Undirected edges as ``(i, j)`` pairs of node indices.
    coupling : np.ndarray
        Per-edge ``J_ij``, shape ``(len(edges),)``, aligned with ``edges``.
    boundary : BoundaryCondition
        The boundary condition the graph was built under. Carried for
        provenance and to dispatch the 1-D chain to its exact sampler
        (:func:`is_open_chain`); a hand-built graph that names no lattice may
        pick either value, since generic Gibbs sampling does not consult it.
    shape : tuple[int, ...] | None
        Lattice shape that produced this graph, if built by
        :func:`lattice_graph`; ``None`` for a graph built directly.

    Raises
    ------
    ValueError
        If ``coupling`` does not have one entry per edge, or an edge
        references a node index outside ``[0, n_nodes)``.
    """

    n_nodes: int
    edges: tuple[tuple[int, int], ...]
    coupling: np.ndarray
    boundary: BoundaryCondition
    shape: tuple[int, ...] | None = None

    def __post_init__(self) -> None:
        if self.coupling.shape != (len(self.edges),):
            msg = (
                f"coupling has shape {self.coupling.shape}, expected "
                f"({len(self.edges)},) -- one entry per edge"
            )
            raise ValueError(msg)
        for edge in self.edges:
            i, j = edge
            if not (0 <= i < self.n_nodes and 0 <= j < self.n_nodes):
                msg = f"edge {edge} references a node outside [0, {self.n_nodes})"
                raise ValueError(msg)


def lattice_graph(
    shape: tuple[int, ...], boundary: BoundaryCondition, coupling: float
) -> PottsGraph:
    """Build an N-D lattice as a :class:`PottsGraph` with uniform edge coupling.

    Nodes are indexed by ``np.ravel_multi_index`` over ``shape`` (row-major).
    A 1-D chain is ``lattice_graph((L,), BoundaryCondition.OPEN, J)``: not a
    separate type, this construction at ``ndim = 1`` -- the graph
    :func:`is_open_chain` recognizes for the exact sampler in
    ``phylo.sim.potts``.

    Parameters
    ----------
    shape : tuple[int, ...]
        Extent along each of ``ndim = len(shape)`` dimensions, each >= 1.
    boundary : BoundaryCondition
        Applied uniformly across every dimension.
    coupling : float
        Scalar ``J`` shared by every edge.

    Returns
    -------
    PottsGraph
        ``n_nodes == prod(shape)``. Edge count is
        ``sum_d (shape[d] - 1) * prod(other dims)`` under ``OPEN``, or
        ``ndim * prod(shape)`` under ``PERIODIC`` (docs/tex/main.tex,
        "Potts Models in an External Field").

    Raises
    ------
    ValueError
        If ``shape`` is empty, an extent is < 1, or ``boundary`` is
        ``PERIODIC`` with an extent < 2 (a length-1 periodic dimension has no
        distinct neighbour to wrap to).
    """
    if not shape:
        msg = "shape must have at least one dimension"
        raise ValueError(msg)
    if any(extent < 1 for extent in shape):
        msg = f"every lattice extent must be >= 1, got {shape}"
        raise ValueError(msg)
    if boundary is BoundaryCondition.PERIODIC and any(extent < 2 for extent in shape):
        msg = f"periodic boundary requires every extent >= 2, got {shape}"
        raise ValueError(msg)

    edges: list[tuple[int, int]] = []
    for index in product(*(range(extent) for extent in shape)):
        node = int(np.ravel_multi_index(index, shape))
        for axis, extent in enumerate(shape):
            if index[axis] + 1 < extent:
                neighbor = list(index)
                neighbor[axis] += 1
                edges.append((node, int(np.ravel_multi_index(tuple(neighbor), shape))))
            elif boundary is BoundaryCondition.PERIODIC:
                neighbor = list(index)
                neighbor[axis] = 0
                edges.append((node, int(np.ravel_multi_index(tuple(neighbor), shape))))

    return PottsGraph(
        n_nodes=int(np.prod(shape)),
        edges=tuple(edges),
        coupling=np.full(len(edges), float(coupling)),
        boundary=boundary,
        shape=tuple(shape),
    )


def is_open_chain(graph: PottsGraph) -> bool:
    """Whether ``graph`` is an open 1-D chain, i.e. built by ``lattice_graph((L,), OPEN, J)``.

    ``phylo.sim.potts.simulate_potts`` dispatches to the exact
    backward-message sampler exactly when this holds; a periodic ring or any
    ``ndim >= 2`` lattice is sampled by generic Gibbs MCMC instead, since the
    exact recursion assumes an unclosed chain.
    """
    return (
        graph.shape is not None
        and len(graph.shape) == 1
        and graph.boundary is BoundaryCondition.OPEN
    )
