"""QA figure: agreement between the likelihood backends.

The likelihood engine makes two correctness claims, and this figure shows
both. Panel (a): every backend agrees with brute-force marginalization over
internal states on a small tree, where that exhaustive sum is tractable and
is an independent algorithm rather than a second opinion from the same
recursion. Panel (b): the accelerated backends agree with the vectorized
NumPy reference at the full fixture sizes, where brute force is not
available.

Renders what `phylo.likelihood` computed; it reimplements no recursion
(`qa/CLAUDE.md`).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure

from phylo.likelihood import pruning, pruning_rust, pruning_torch
from phylo.likelihood.brute_force import brute_force_log_likelihood
from phylo.qa.figure import QAFigure, write_qa_figure
from phylo.qa.style import INK_MUTED, ONE_COLUMN_WIDE, letter_style, series_style
from phylo.sim.params import SimulationParams, load_simulation_params
from phylo.sim.simulate import simulate_alignment

# The tolerance tests/regression/test_pruning_rust.py and
# test_pruning_torch.py pin the accelerated backends at.
BACKEND_TOLERANCE = 1e-9

# The relative floor a float64 sum can reach, for panel (b)'s reference line.
FLOAT64_EPS = float(np.finfo(np.float64).eps)

# Brute force costs k^(internal nodes) per site, so the exhaustive panel runs
# on a deliberately small slice rather than the whole fixture.
_BRUTE_FORCE_SITES = 400


@dataclass(frozen=True)
class BackendAgreement:
    """Absolute log-likelihood deviations for one dataset.

    Parameters
    ----------
    label : str
        Short name for the dataset, used as an axis tick.
    n_taxa : int
        Number of leaves.
    n_sites : int
        Number of sites scored.
    reference : float
        The reference log-likelihood the deviations are measured against.
    deviations : dict[str, float]
        Backend name to ``|lnL_backend - lnL_reference|``.
    relative : dict[str, float]
        Backend name to ``|lnL_backend - lnL_reference| / |lnL_reference|``.
        The scale-free comparison: the total log-likelihood is a sum over
        sites, so an absolute deviation grows with the site count while a
        relative one does not.
    """

    label: str
    n_taxa: int
    n_sites: int
    reference: float
    deviations: dict[str, float]
    relative: dict[str, float]


def _alignment_slice(
    params: SimulationParams, n_sites: int
) -> tuple[dict[str, np.ndarray], int]:
    """Simulate ``params`` and take the leading ``n_sites`` columns."""
    dataset = simulate_alignment(
        tau=params.tau,
        k=params.k,
        pi=params.pi,
        seed=params.seed,
        n_sites=min(n_sites, params.n_sites),
    )
    alignment = dict(dataset.alignment)
    return alignment, len(next(iter(alignment.values())))


def agreement_against_brute_force(params: SimulationParams) -> BackendAgreement:
    """Deviations of every backend from exhaustive marginalization.

    Parameters
    ----------
    params : SimulationParams
        Fixture to score. Must be small enough for brute force.

    Returns
    -------
    BackendAgreement
        Deviations keyed by backend name, against the brute-force reference.
    """
    alignment, n_sites = _alignment_slice(params, _BRUTE_FORCE_SITES)
    reference = brute_force_log_likelihood(params.tau, params.k, params.pi, alignment)

    numpy_value = pruning.log_likelihood(params.tau, params.k, params.pi, alignment)
    rust_value = pruning_rust.log_likelihood(params.tau, params.k, params.pi, alignment)
    torch_value = float(
        pruning_torch.log_likelihood(
            params.tau,
            params.k,
            params.pi,
            alignment,
            pruning_torch.branch_lengths_from_tree(params.tau),
        )
    )

    return BackendAgreement(
        label=f"{len(alignment)} taxa\n{n_sites} sites",
        n_taxa=len(alignment),
        n_sites=n_sites,
        reference=reference,
        deviations={
            "NumPy": abs(numpy_value - reference),
            "PyTorch": abs(torch_value - reference),
            "Rust": abs(rust_value - reference),
        },
        relative={
            "NumPy": abs(numpy_value - reference) / abs(reference),
            "PyTorch": abs(torch_value - reference) / abs(reference),
            "Rust": abs(rust_value - reference) / abs(reference),
        },
    )


def agreement_against_numpy(params: SimulationParams) -> BackendAgreement:
    """Deviations of the accelerated backends from the NumPy reference.

    Parameters
    ----------
    params : SimulationParams
        Fixture to score, at its own full site count.

    Returns
    -------
    BackendAgreement
        Deviations keyed by backend name, against the NumPy oracle.
    """
    alignment, n_sites = _alignment_slice(params, params.n_sites)
    reference = pruning.log_likelihood(params.tau, params.k, params.pi, alignment)

    rust_value = pruning_rust.log_likelihood(params.tau, params.k, params.pi, alignment)
    torch_value = float(
        pruning_torch.log_likelihood(
            params.tau,
            params.k,
            params.pi,
            alignment,
            pruning_torch.branch_lengths_from_tree(params.tau),
        )
    )

    return BackendAgreement(
        label=f"{len(alignment)} taxa\n{n_sites // 1000}k sites",
        n_taxa=len(alignment),
        n_sites=n_sites,
        reference=reference,
        deviations={
            "PyTorch": abs(torch_value - reference),
            "Rust": abs(rust_value - reference),
        },
        relative={
            "PyTorch": abs(torch_value - reference) / abs(reference),
            "Rust": abs(rust_value - reference) / abs(reference),
        },
    )


def _floor(deviation: float) -> float:
    """Plot an exact zero at the axis floor, so it is visible on a log scale."""
    return max(deviation, 1e-17)


def build_figure(
    brute_force: BackendAgreement, at_scale: list[BackendAgreement]
) -> tuple[Figure, str]:
    """Render both agreement panels.

    Parameters
    ----------
    brute_force : BackendAgreement
        Small-tree agreement against exhaustive marginalization.
    at_scale : list[BackendAgreement]
        Full-size agreement against the NumPy reference, one per fixture.

    Returns
    -------
    tuple[matplotlib.figure.Figure, str]
        The figure, and its caption.
    """
    with letter_style():
        fig, (left, right) = plt.subplots(
            1, 2, figsize=ONE_COLUMN_WIDE, width_ratios=(1.0, 1.5)
        )

        names = list(brute_force.deviations)
        for index, name in enumerate(names):
            style = series_style(index)
            left.plot(
                [index],
                [_floor(brute_force.deviations[name])],
                marker=style["marker"],
                color=style["color"],
                linestyle="none",
                markerfacecolor="white",
                markeredgewidth=1.2,
                markersize=6,
            )
        left.set_xticks(range(len(names)), names, rotation=30, ha="right")
        left.set_yscale("log")
        left.set_ylabel(r"$|\Delta \ln L|$ vs brute force")
        left.set_title("(a) exhaustive oracle", loc="left")
        left.set_xlim(-0.6, len(names) - 0.4)

        scale_names = list(at_scale[0].deviations)
        positions = np.arange(len(at_scale))
        for index, name in enumerate(scale_names):
            style = series_style(index + 1)
            right.plot(
                positions,
                [_floor(row.relative[name]) for row in at_scale],
                marker=style["marker"],
                color=style["color"],
                # Markers only: the x axis is three distinct fixtures, not a
                # continuum, so a connecting line would imply interpolation
                # between them.
                linestyle="none",
                markerfacecolor="white",
                markeredgewidth=1.2,
                markersize=6,
                label=name,
            )
        right.axhline(
            FLOAT64_EPS, color=INK_MUTED, linewidth=0.8, linestyle=":", zorder=1
        )
        right.annotate(
            "float64 epsilon",
            xy=(positions[0] - 0.35, FLOAT64_EPS),
            xytext=(0, 5),
            textcoords="offset points",
            color=INK_MUTED,
            fontsize=7.5,
        )
        right.set_xticks(positions, [row.label for row in at_scale])
        right.set_yscale("log")
        right.set_ylabel(r"$|\Delta \ln L| \, / \, |\ln L|$ vs NumPy")
        right.set_title("(b) at fixture scale", loc="left")
        right.set_xlim(-0.5, len(at_scale) - 0.5)
        right.legend(loc="upper left")

        fig.tight_layout()

    worst_bf = max(brute_force.deviations.values())
    worst_abs = max(max(row.deviations.values()) for row in at_scale)
    worst_rel = max(max(row.relative.values()) for row in at_scale)
    caption = (
        f"Backend agreement. (a) All three backends against brute-force "
        f"marginalization over internal states on a {brute_force.n_taxa}-taxon "
        f"tree at {brute_force.n_sites} sites, where the exhaustive sum is "
        f"tractable and is an independent algorithm rather than a second "
        f"opinion from the same recursion; largest deviation {worst_bf:.2e}, "
        f"within the {BACKEND_TOLERANCE:.0e} absolute tolerance the regression "
        f"tests pin at these sizes. (b) The accelerated backends against the "
        f"vectorized NumPy reference at full fixture sizes, where brute force "
        f"is not available, plotted as relative deviation; largest "
        f"{worst_rel:.2e}, at the float64 floor (dotted). Relative rather than "
        f"absolute because the total log-likelihood is a sum over sites: the "
        f"same agreement reads as {worst_abs:.2e} absolute at these sizes, so "
        f"an absolute tolerance fixed at small sizes does not transfer. "
        f"Points at the axis floor are exact agreement."
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
    parser.add_argument("--params", type=Path, action="append", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    fixtures = [load_simulation_params(path) for path in args.params]
    brute_force = agreement_against_brute_force(fixtures[0])
    at_scale = [agreement_against_numpy(params) for params in fixtures]

    fig, caption = build_figure(brute_force, at_scale)
    try:
        return write_qa_figure(args.output_dir, "likelihood_backends", fig, caption)
    finally:
        plt.close(fig)


if __name__ == "__main__":
    main()
