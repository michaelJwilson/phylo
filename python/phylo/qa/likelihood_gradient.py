"""QA figure: autograd gradients against central finite differences.

Milestone 4 rests on the gradient of the log-likelihood with respect to
branch lengths being right. `torch.autograd` produces it analytically by
differentiating the pruning recursion; central finite differences of the
independent NumPy likelihood produce it numerically. The two are computed by
different code over different implementations, so agreement is evidence
rather than self-consistency.

Panel (a) plots one against the other, per branch. Panel (b) shows why the
finite-difference step cannot simply be made small: truncation error falls as
the step shrinks while cancellation error grows, so the total is
U-shaped and the comparison is only meaningful near the minimum.

Renders what `phylo.likelihood` computed; it reimplements no recursion
(`qa/CLAUDE.md`).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from phylo.likelihood import pruning, pruning_torch
from phylo.qa.figure import QAFigure, write_qa_figure
from phylo.qa.style import INK_MUTED, ONE_COLUMN_WIDE, letter_style, series_style
from phylo.sim.params import SimulationParams, load_simulation_params
from phylo.sim.simulate import simulate_alignment
from phylo.sim.tree import Node, edges

# The step tests/regression/test_pruning_torch.py differentiates at.
FD_STEP = 1e-6

# That test pins an ABSOLUTE tolerance of 1e-6, at 30 sites. This figure runs
# at a realistic site count, where the gradient -- like the log-likelihood
# itself -- scales with the number of sites, so the same agreement reads far
# larger in absolute terms. Disagreement is therefore reported relative to the
# gradient magnitude, which is scale-free.
TEST_ABSOLUTE_TOLERANCE = 1e-6
TEST_TOLERANCE_SITES = 30
RELATIVE_TOLERANCE = 1e-8

# Sites are cheap here relative to the finite-difference sweep, which
# re-scores the whole alignment twice per branch per step.
_SITES = 2000
_STEPS = (1e-2, 1e-3, 1e-4, 1e-5, 1e-6, 1e-7, 1e-8, 1e-9)


def _with_branch_lengths(tau: Node, lengths: dict[str, float]) -> Node:
    """Rebuild ``tau`` with each non-root node's length taken from ``lengths``."""
    children = tuple(_with_branch_lengths(child, lengths) for child in tau.children)
    if tau.branch_length is None:
        return Node(name=tau.name, branch_length=None, children=children)
    return Node(name=tau.name, branch_length=lengths[tau.name], children=children)


def _numpy_log_likelihood(
    params: SimulationParams,
    alignment: dict[str, np.ndarray],
    lengths: dict[str, float],
) -> float:
    """Score ``alignment`` with the NumPy backend at the given branch lengths."""
    tau = _with_branch_lengths(params.tau, lengths)
    return pruning.log_likelihood(tau, params.k, params.pi, alignment)


def gradients(
    params: SimulationParams, step: float = FD_STEP
) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Analytic and finite-difference gradients, per branch.

    Parameters
    ----------
    params : SimulationParams
        Fixture supplying the topology and the alignment to score.
    step : float
        Central finite-difference step.

    Returns
    -------
    tuple[list[str], np.ndarray, np.ndarray]
        Branch names, autograd gradients, and finite-difference gradients,
        index-matched.
    """
    dataset = simulate_alignment(
        tau=params.tau,
        k=params.k,
        pi=params.pi,
        seed=params.seed,
        n_sites=min(_SITES, params.n_sites),
    )
    alignment = dict(dataset.alignment)

    names = pruning_torch.branch_order(params.tau)
    branch_lengths = pruning_torch.branch_lengths_from_tree(params.tau)
    branch_lengths.requires_grad_(True)

    value = pruning_torch.log_likelihood(
        params.tau, params.k, params.pi, alignment, branch_lengths
    )
    # torch ships no annotation for Tensor.backward, so mypy --strict
    # sees an untyped call in typed context; the gradient it populates is
    # checked immediately below.
    value.backward()  # type: ignore[no-untyped-call]
    assert branch_lengths.grad is not None
    autograd = branch_lengths.grad.detach().numpy().copy()

    base = {
        child.name: child.branch_length
        for _, child in edges(params.tau)
        if child.branch_length is not None
    }
    finite = np.zeros(len(names))
    for index, name in enumerate(names):
        up = dict(base)
        up[name] = base[name] + step
        down = dict(base)
        down[name] = base[name] - step
        finite[index] = (
            _numpy_log_likelihood(params, alignment, up)
            - _numpy_log_likelihood(params, alignment, down)
        ) / (2.0 * step)

    return names, autograd, finite


def _relative_disagreement(autograd: np.ndarray, finite: np.ndarray) -> float:
    """Largest ``|autograd - finite|`` relative to the gradient magnitude."""
    scale = np.maximum(np.abs(autograd), np.finfo(np.float64).tiny)
    return float(np.max(np.abs(autograd - finite) / scale))


def step_sweep(params: SimulationParams) -> tuple[list[float], list[float]]:
    """Largest relative autograd/finite-difference disagreement per step size.

    Parameters
    ----------
    params : SimulationParams
        Fixture to differentiate.

    Returns
    -------
    tuple[list[float], list[float]]
        The step sizes, and the largest absolute disagreement at each.
    """
    worst: list[float] = []
    for step in _STEPS:
        _, autograd, finite = gradients(params, step=step)
        worst.append(_relative_disagreement(autograd, finite))
    return list(_STEPS), worst


def build_figure(
    names: list[str],
    autograd: np.ndarray,
    finite: np.ndarray,
    steps: list[float],
    worst: list[float],
) -> tuple[Figure, str]:
    """Render the agreement and the step-size sweep.

    Parameters
    ----------
    names : list[str]
        Branch names, index-matched to the gradients.
    autograd : np.ndarray
        Analytic gradients from ``torch.autograd``.
    finite : np.ndarray
        Central finite-difference gradients of the NumPy likelihood.
    steps : list[float]
        Finite-difference steps swept.
    worst : list[float]
        Largest disagreement at each step.

    Returns
    -------
    tuple[matplotlib.figure.Figure, str]
        The figure, and its caption.
    """
    with letter_style():
        fig, (left, right) = plt.subplots(1, 2, figsize=ONE_COLUMN_WIDE)

        style = series_style(0)
        span = [
            float(min(finite.min(), autograd.min())),
            float(max(finite.max(), autograd.max())),
        ]
        pad = 0.06 * (span[1] - span[0])
        line = [span[0] - pad, span[1] + pad]
        left.plot(line, line, color=INK_MUTED, linewidth=0.8, linestyle=":", zorder=1)
        left.plot(
            finite,
            autograd,
            marker=style["marker"],
            color=style["color"],
            linestyle="none",
            markerfacecolor="white",
            markeredgewidth=1.2,
            markersize=6,
            zorder=2,
        )
        left.annotate(
            "y = x",
            xy=(line[1], line[1]),
            xytext=(-6, -12),
            textcoords="offset points",
            ha="right",
            color=INK_MUTED,
            fontsize=7.5,
        )
        left.set_xlabel(r"finite difference $\partial \ln L / \partial t$")
        left.set_ylabel(r"autograd $\partial \ln L / \partial t$")
        left.set_title(f"(a) {len(names)} branches", loc="left")
        left.set_xlim(*line)
        left.set_ylim(*line)

        sweep = series_style(2)
        right.plot(
            steps,
            worst,
            marker=sweep["marker"],
            color=sweep["color"],
            linestyle="-",
            markerfacecolor="white",
            markeredgewidth=1.2,
        )
        right.axhline(
            RELATIVE_TOLERANCE,
            color=INK_MUTED,
            linewidth=0.8,
            linestyle=":",
            zorder=1,
        )
        right.annotate(
            f"relative {RELATIVE_TOLERANCE:.0e}",
            xy=(steps[0], RELATIVE_TOLERANCE),
            xytext=(0, 5),
            textcoords="offset points",
            color=INK_MUTED,
            fontsize=7.5,
        )
        right.set_xscale("log")
        right.set_yscale("log")
        right.invert_xaxis()
        right.set_xlabel("finite-difference step $h$")
        right.set_ylabel("largest relative disagreement")
        right.set_title("(b) step sweep", loc="left")

        fig.tight_layout()

    realized_abs = float(np.max(np.abs(autograd - finite)))
    realized = _relative_disagreement(autograd, finite)
    best_index = int(np.argmin(worst))
    caption = (
        f"Analytic gradients against central finite differences, over the "
        f"{len(names)} branches of the fixture tree. (a) Autograd through the "
        f"PyTorch pruning recursion against finite differences of the "
        f"independent NumPy likelihood, at step h = {FD_STEP:.0e}; points lie "
        f"on y = x, largest relative disagreement {realized:.2e}. Two "
        f"implementations and two methods, so agreement is evidence rather "
        f"than self-consistency. (b) The same disagreement swept over h, x "
        f"axis reversed so h decreases rightwards. The curve is U-shaped: "
        f"truncation error falls as h shrinks while floating-point "
        f"cancellation grows, best here at h = {steps[best_index]:.0e} "
        f"({worst[best_index]:.2e}). A finite-difference check is only "
        f"meaningful near that minimum, which is why the step is stated. "
        f"Disagreement is reported relative to the gradient magnitude: the "
        f"regression tests pin an absolute {TEST_ABSOLUTE_TOLERANCE:.0e} at "
        f"{TEST_TOLERANCE_SITES} sites, but the gradient scales with the site "
        f"count, so the same agreement reads as {realized_abs:.2e} absolute "
        f"here and an absolute bound fixed at one size does not transfer."
    )
    return fig, caption


def main(argv: list[str] | None = None) -> QAFigure:
    """Render the figure from the command line.

    Parameters
    ----------
    argv : list[str] | None
        Argument vector; ``None`` reads ``sys.argv``.

    Returns
    -------
    QAFigure
        Paths written, and the caption.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--params", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    params = load_simulation_params(args.params)
    names, autograd, finite = gradients(params)
    steps, worst = step_sweep(params)

    fig, caption = build_figure(names, autograd, finite, steps, worst)
    try:
        return write_qa_figure(args.output_dir, "likelihood_gradient", fig, caption)
    finally:
        plt.close(fig)


if __name__ == "__main__":
    main()
