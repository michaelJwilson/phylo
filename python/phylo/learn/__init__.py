"""Reinforcement learning over discrete search problems.

Infrastructure, not application: nothing here knows what a tree is, and a
test asserts it. The interface is :class:`~phylo.learn.environment.Environment`
and the reference instance is a Potts landscape, exactly as ``phylo.opt``
pairs :class:`~phylo.opt.objective.Objective` with a Potts chain and an HMM.

Root ``CLAUDE.md`` re-exports nothing from a package's top level, so import
submodule contents explicitly.
"""
