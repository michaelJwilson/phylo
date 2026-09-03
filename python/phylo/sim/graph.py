"""Undirected graphs for the Potts model, and N-D lattice constructors.

An N-D lattice is a constructed case of a general graph, not a second
representation: :func:`lattice_graph` builds a :class:`PottsGraph`, and
nothing downstream distinguishes a lattice from a hand-built graph except
the ``shape``/``boundary`` metadata a lattice happens to carry.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product


@dataclass(frozen=True)
class PottsGraph:
    """An undirected graph carrying a per-edge Potts coupling.

    Parameters
    ----------
    n_nodes : int
        Number of sites, indexed ``0`` to ``n_nodes - 1``.
    edges : tuple[tuple[int, int], ...]
        Undirected edges as ``(i, j)`` pairs. Not deduplicated: a periodic
        lattice of extent 2 along some dimension legitimately produces the
        same pair twice (the "+1" and "-1" neighbour coincide), which reads
        as a doubled bond rather than a single one -- the edge count formula
        `lattice_graph` is validated against expects exactly this.
    coupling : tuple[float, ...]
        Coupling ``J`` per edge, same order and length as ``edges``.
    shape : tuple[int, ...] | None
        The lattice extent along each dimension, if this graph was built by
        :func:`lattice_graph`; ``None`` for a graph built directly.
    boundary : str | None
        ``"open"`` or ``"periodic"``, if this graph was built by
        :func:`lattice_graph`; ``None`` for a graph built directly.
    """

    n_nodes: int
    edges: tuple[tuple[int, int], ...]
    coupling: tuple[float, ...]
    shape: tuple[int, ...] | None = None
    boundary: str | None = None

    def is_open_chain(self) -> bool:
        """Whether this graph is a 1-D lattice with an open boundary.

        The one case with a cheap exact sampler (:mod:`phylo.sim.potts`'s
        backward-message recursion, the same one
        :func:`phylo.opt.potts.log_partition` sums via transfer matrix) --
        a periodic ring is a different, cyclic recursion, so it is excluded
        here rather than approximated by the open-chain code.
        """
        return (
            self.shape is not None and len(self.shape) == 1 and self.boundary == "open"
        )


def lattice_graph(shape: tuple[int, ...], boundary: str, coupling: float) -> PottsGraph:
    """Build an N-D lattice as a :class:`PottsGraph`, with a uniform coupling.

    A 1-D chain is ``lattice_graph((length,), boundary, coupling)``, not a
    separate type.

    Parameters
    ----------
    shape : tuple[int, ...]
        Extent along each of ``N`` dimensions, each ``>= 2``.
    boundary : {"open", "periodic"}
        ``"open"``: no wraparound edges, so a boundary node has fewer
        neighbours. ``"periodic"``: every dimension wraps.
    coupling : float
        Uniform ``J`` applied to every edge.

    Returns
    -------
    PottsGraph
        ``n_nodes = prod(shape)``, nodes indexed by the standard row-major
        (C-order) unraveling of ``shape``, matching
        ``numpy.ravel_multi_index``.

    Raises
    ------
    ValueError
        If ``shape`` is empty, any extent is below 2, or ``boundary`` is not
        one of the two recognized values.
    """
    if not shape:
        msg = "shape must have at least one dimension"
        raise ValueError(msg)
    if any(extent < 2 for extent in shape):
        msg = f"every extent in shape must be >= 2, got {shape}"
        raise ValueError(msg)
    if boundary not in ("open", "periodic"):
        msg = f"boundary must be 'open' or 'periodic', got {boundary!r}"
        raise ValueError(msg)

    strides = [1] * len(shape)
    for dim in range(len(shape) - 2, -1, -1):
        strides[dim] = strides[dim + 1] * shape[dim + 1]

    def index(coordinate: tuple[int, ...]) -> int:
        return sum(c * s for c, s in zip(coordinate, strides, strict=True))

    edges: list[tuple[int, int]] = []
    for coordinate in product(*(range(extent) for extent in shape)):
        node = index(coordinate)
        for dim, extent in enumerate(shape):
            if boundary == "periodic":
                neighbor = list(coordinate)
                neighbor[dim] = (coordinate[dim] + 1) % extent
                edges.append((node, index(tuple(neighbor))))
            elif coordinate[dim] + 1 < extent:
                neighbor = list(coordinate)
                neighbor[dim] += 1
                edges.append((node, index(tuple(neighbor))))

    n_nodes = 1
    for extent in shape:
        n_nodes *= extent

    return PottsGraph(
        n_nodes=n_nodes,
        edges=tuple(edges),
        coupling=(coupling,) * len(edges),
        shape=shape,
        boundary=boundary,
    )
