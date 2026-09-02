"""The phylogenetic instance of ``phylo.opt.objective.Objective``.

It lives here rather than in ``phylo.opt`` because ``opt/CLAUDE.md`` forbids
that package from importing any application module, and a test enforces it
(issue #63). The dependency runs one way -- an application knows the
optimization vocabulary, the optimizer knows no models -- and this file is
that direction made concrete: it imports ``phylo.opt.constrain`` and is
imported by nothing in ``phylo.opt``.

**Not every branch length is identifiable, and which ones are depends on the
root.** Under a reversible model the likelihood is invariant to where the
root sits along the branch it subdivides (Felsenstein, *Inferring
Phylogenies*, ch. 16, the "pulley principle"), so on a **rooted binary** tree
the two branches below the root are confounded: only their sum is estimable.
Measured on the 8-taxon fixture, shifting mass between them across a 9:1
range moves the log-likelihood by at most 3.6e-12 -- floating-point noise --
while the same shift between two non-root siblings moves it by 14.7. Fitting
them separately would leave the observed information singular and every
confidence interval undefined.

So the pair is fitted as **one** parameter and reported as its sum. On a tree
in the trifurcating-root convention there is no such pair and every branch is
estimable, which is the usual reason phylogenetic inference is done on
unrooted topologies.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import torch

from phylo.likelihood import pruning_torch
from phylo.opt.constrain import free_from_positive, positive
from phylo.sim.tree import Node

# Starting length for every branch, in expected substitutions per site. Small
# and uninformative rather than fitted from the data: a data-dependent start
# would make the fit's own convergence part of what the recovery test
# measures.
_INITIAL_BRANCH_LENGTH = 0.1


class BranchLengthObjective:
    """Negative log-likelihood of an alignment as a function of branch lengths.

    Parameters
    ----------
    tau : Node
        The topology, held fixed. Branch lengths on the ``Node`` tree are
        ignored -- ``pruning_torch`` takes them as a tensor, per
        ``likelihood/CLAUDE.md``.
    k : int
        Number of states.
    pi : np.ndarray
        Root state distribution, shape ``(k,)``.
    alignment : Mapping[str, np.ndarray]
        Observed states per taxon.
    dtype : torch.dtype
        Precision; ``float64`` by default, since a finite-difference
        derivative check is meaningless in ``float32``.
    device : torch.device | str | None
        Where to run. ``None`` leaves the tensor on the default device.

    Raises
    ------
    ValueError
        If ``tau``'s root has fewer than two children, which is not a tree
        this likelihood is defined on.
    """

    def __init__(
        self,
        tau: Node,
        k: int,
        pi: np.ndarray,
        alignment: Mapping[str, np.ndarray],
        dtype: torch.dtype = torch.float64,
        device: torch.device | str | None = None,
    ) -> None:
        if len(tau.children) < 2:
            msg = (
                f"root {tau.name!r} has {len(tau.children)} children; a tree "
                f"needs a root with at least 2"
            )
            raise ValueError(msg)

        self._tau = tau
        self._k = k
        self._pi = pi
        self._alignment = dict(alignment)
        self._dtype = dtype
        self._device = device

        self._branch_order = pruning_torch.branch_order(tau)
        root_children = [child.name for child in tau.children]
        # The confounded pair, if there is one. Two children means a rooted
        # binary tree and a flat direction; three means the trifurcating-root
        # convention, where every branch stands on its own.
        self._merged: tuple[int, int] | None = (
            (
                self._branch_order.index(root_children[0]),
                self._branch_order.index(root_children[1]),
            )
            if len(root_children) == 2
            else None
        )

    @property
    def parameter_names(self) -> list[str]:
        """Names of the *estimable* parameters, in ``theta`` order.

        One per branch, except that on a rooted binary tree the two branches
        below the root appear once, as ``"a+b"``, because only their sum is
        estimable.
        """
        if self._merged is None:
            return list(self._branch_order)
        first, second = self._merged
        names = [
            name for index, name in enumerate(self._branch_order) if index != second
        ]
        names[names.index(self._branch_order[first])] = (
            f"{self._branch_order[first]}+{self._branch_order[second]}"
        )
        return names

    @property
    def n_parameters(self) -> int:
        """Number of estimable parameters."""
        return len(self._branch_order) - (0 if self._merged is None else 1)

    def initial(self) -> torch.Tensor:
        """A short, uninformative branch length everywhere."""
        return torch.full(
            (self.n_parameters,),
            float(np.log(_INITIAL_BRANCH_LENGTH)),
            dtype=self._dtype,
            device=self._device,
        )

    def constrain(self, theta: torch.Tensor) -> Mapping[str, torch.Tensor]:
        """The estimable branch lengths ``theta`` encodes, in ``parameter_names`` order.

        Parameters
        ----------
        theta : torch.Tensor
            Unconstrained parameters.

        Returns
        -------
        Mapping[str, torch.Tensor]
            ``{"branch_lengths": ...}``, positive, one entry per estimable
            parameter -- so on a rooted binary tree the root pair appears
            once, as its sum.
        """
        return {"branch_lengths": positive(theta)}

    def branch_lengths(self, theta: torch.Tensor) -> torch.Tensor:
        """Expand ``theta`` to one length per branch, in ``branch_order``.

        The estimable sum is split evenly between the two root branches.
        Any split gives the same likelihood -- that is what "confounded"
        means -- so halving is a reporting convention, not an estimate, and
        neither half should be quoted as one.

        Parameters
        ----------
        theta : torch.Tensor
            Unconstrained parameters.

        Returns
        -------
        torch.Tensor
            One positive length per branch, ordered for ``pruning_torch``.
        """
        lengths = positive(theta)
        if self._merged is None:
            return lengths
        first, second = self._merged
        head = lengths[:second]
        tail = lengths[second:]
        halved = head.clone()
        halved[first] = head[first] / 2.0
        return torch.cat([halved, halved[first : first + 1], tail])

    def __call__(self, theta: torch.Tensor) -> torch.Tensor:
        """Negative log-likelihood of the alignment at these branch lengths."""
        return -pruning_torch.log_likelihood(
            self._tau,
            self._k,
            self._pi,
            self._alignment,
            self.branch_lengths(theta),
        )

    def theta_from_truth(self, tau: Node) -> torch.Tensor:
        """Place a tree's own branch lengths in the unconstrained coordinates.

        Parameters
        ----------
        tau : Node
            A tree with the same topology as this objective's, carrying the
            lengths to encode.

        Returns
        -------
        torch.Tensor
            ``theta`` whose estimable parameters are those lengths, with the
            root pair replaced by its sum.
        """
        lengths = pruning_torch.branch_lengths_from_tree(tau, dtype=self._dtype)
        if self._merged is not None:
            first, second = self._merged
            summed = lengths[first] + lengths[second]
            keep = [index for index in range(lengths.numel()) if index != second]
            lengths = lengths[keep].clone()
            lengths[keep.index(first)] = summed
        return free_from_positive(lengths)
