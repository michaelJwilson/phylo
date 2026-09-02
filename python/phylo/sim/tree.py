"""Minimal tree representation for the simulator.

Topology is an input to simulation (drawn from ``simulation_params.yaml``),
never inferred, so this is deliberately not a general Newick parser --
serialization to Newick is the only direction the simulator needs.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass


@dataclass(frozen=True)
class Node:
    """A node in a rooted tree.

    Parameters
    ----------
    name : str
        Label for the node. Leaf names double as alignment taxon names.
    branch_length : float | None
        Length of the edge above this node, in expected substitutions per
        site. ``None`` at the root, where there is no incoming edge.
    children : tuple[Node, ...]
        Child nodes, empty for a leaf.
    """

    name: str
    branch_length: float | None
    children: tuple[Node, ...] = ()

    @property
    def is_leaf(self) -> bool:
        """Whether this node has no children."""
        return not self.children


def preorder(root: Node) -> Iterator[Node]:
    """Yield every node in the tree rooted at ``root``, parent before children.

    Parameters
    ----------
    root : Node
        Root of the tree to walk.

    Returns
    -------
    Iterator[Node]
        Nodes in pre-order.
    """
    yield root
    for child in root.children:
        yield from preorder(child)


def edges(root: Node) -> Iterator[tuple[Node, Node]]:
    """Yield every ``(parent, child)`` edge in the tree rooted at ``root``.

    Parameters
    ----------
    root : Node
        Root of the tree to walk.

    Returns
    -------
    Iterator[tuple[Node, Node]]
        Parent/child pairs, one per edge.
    """
    for child in root.children:
        yield root, child
        yield from edges(child)


def to_newick(root: Node) -> str:
    """Serialize a tree to Newick format.

    Parameters
    ----------
    root : Node
        Root of the tree to serialize. Its ``branch_length`` is ignored, per
        the Newick convention that the root carries no incoming edge.

    Returns
    -------
    str
        The tree in Newick format, terminated with ``;``.
    """
    return f"{_to_newick(root)};"


def _to_newick(node: Node) -> str:
    if node.is_leaf:
        label = node.name
    else:
        inner = ",".join(_to_newick(child) for child in node.children)
        label = f"({inner}){node.name}"
    if node.branch_length is None:
        return label
    return f"{label}:{node.branch_length}"
