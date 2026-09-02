"""QA figure: do the fitted intervals cover the truth at their nominal rate?

`opt/CLAUDE.md` makes recovery the acceptance test, and a Wald interval built
from the observed information is an *asymptotic* claim: it is exact only in
the limit of large samples. This figure is the evidence for that claim rather
than an assertion of it, and it is what separates a slightly optimistic
approximation from a wrong formula -- the first shrinks as the sample grows,
the second does not.

Both reference instances are refitted at a range of data sizes, many
independent datasets at each, and the fraction of 95 percent intervals
containing the generating value is plotted with its binomial uncertainty.

Renders what `phylo.opt` computed; it reimplements no model and no optimizer
(`qa/CLAUDE.md`).
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.figure import Figure

from phylo.opt.fit import constrained_standard_errors, covers, fit
from phylo.opt.hmm import (
    HmmObjective,
    HmmParams,
    align_states,
    load_hmm_params,
    simulate_sequences,
)
from phylo.opt.potts import (
    PottsObjective,
    PottsParams,
    load_potts_params,
    simulate_chains,
)
from phylo.qa.figure import QAFigure, write_qa_figure
from phylo.qa.style import INK_MUTED, ONE_COLUMN, letter_style, series_style

NOMINAL = 0.95

# Sizes and replicate counts, chosen so the whole figure stays inside a
# minute of the technical-document build. The Potts fit is two orders of
# magnitude cheaper than the HMM's, so it gets both more sizes and more
# replicates; the HMM's largest size is where the asymptotics are meant to
# be visible, so it is the one that must not be dropped.
POTTS_SIZES = ((100, 40), (400, 40), (1600, 25))
HMM_SIZES = ((150, 8), (600, 6), (2400, 4))


def potts_coverage(
    params: PottsParams, n_chains: int, replicates: int
) -> tuple[int, int]:
    """Count covering intervals over independent Potts datasets.

    Parameters
    ----------
    params : PottsParams
        The generating truth; its ``n_chains`` is overridden.
    n_chains : int
        Chains per dataset.
    replicates : int
        Independent datasets, each with its own seed.

    Returns
    -------
    tuple[int, int]
        Intervals covering, and intervals checked.
    """
    truth = torch.cat(
        [
            torch.tensor([params.coupling], dtype=torch.float64),
            torch.as_tensor(params.field),
        ]
    )
    covered = 0
    total = 0
    for replicate in range(replicates):
        drawn = replace(params, seed=params.seed + 7919 * replicate, n_chains=n_chains)
        objective = PottsObjective(simulate_chains(drawn), drawn.n_states)
        result = fit(objective)
        estimate = objective.constrain(result.theta)
        error = constrained_standard_errors(objective, result.theta)
        point = torch.cat([estimate["coupling"].reshape(1), estimate["field"]])
        spread = torch.cat([error["coupling"].reshape(1), error["field"]])
        hits = covers(point, spread, truth)
        covered += int(hits.sum())
        total += hits.numel()
    return covered, total


def hmm_coverage(
    params: HmmParams, n_sequences: int, replicates: int
) -> tuple[int, int]:
    """Count covering intervals over independent HMM datasets.

    The hidden-state permutation is aligned before comparing, since the
    likelihood is invariant to it.

    Parameters
    ----------
    params : HmmParams
        The generating truth; its ``n_sequences`` is overridden.
    n_sequences : int
        Sequences per dataset.
    replicates : int
        Independent datasets, each with its own seed.

    Returns
    -------
    tuple[int, int]
        Intervals covering, and intervals checked.
    """
    truths = {
        "log_initial": torch.log(torch.as_tensor(params.initial)),
        "log_transition": torch.log(torch.as_tensor(params.transition)),
        "log_emission": torch.log(torch.as_tensor(params.emission)),
    }
    covered = 0
    total = 0
    for replicate in range(replicates):
        drawn = replace(
            params, seed=params.seed + 7919 * replicate, n_sequences=n_sequences
        )
        objective = HmmObjective(
            simulate_sequences(drawn), drawn.n_states, drawn.n_symbols
        )
        result = fit(objective)
        estimate = objective.constrain(result.theta)
        error = constrained_standard_errors(objective, result.theta)
        order = list(
            align_states(estimate["log_emission"], torch.as_tensor(params.emission))
        )
        for name, reference in truths.items():
            point, spread = estimate[name], error[name]
            if name == "log_transition":
                point, spread = point[order][:, order], spread[order][:, order]
            else:
                point, spread = point[order], spread[order]
            hits = covers(point, spread, reference)
            covered += int(hits.sum())
            total += hits.numel()
    return covered, total


def build_figure(
    potts: list[tuple[int, int, int]],
    hmm: list[tuple[int, int, int]],
) -> tuple[Figure, str]:
    """Assemble the coverage figure and its caption.

    Parameters
    ----------
    potts, hmm : list[tuple[int, int, int]]
        One ``(size, covered, total)`` per data size.

    Returns
    -------
    tuple[matplotlib.figure.Figure, str]
        The figure and its caption text.
    """
    with letter_style():
        fig, ax = plt.subplots(figsize=ONE_COLUMN)
        ax.axhline(NOMINAL, color=INK_MUTED, linestyle=":", linewidth=0.8, zorder=1)
        ax.annotate(
            "nominal 0.95",
            xy=(0.02, NOMINAL),
            xycoords=("axes fraction", "data"),
            va="bottom",
            color=INK_MUTED,
            fontsize="small",
        )
        for index, (series, label) in enumerate(((potts, "Potts"), (hmm, "HMM"))):
            sizes = np.array([size for size, _, _ in series], dtype=float)
            rates = np.array([hit / total for _, hit, total in series])
            errors = np.array(
                [
                    (rate * (1.0 - rate) / total) ** 0.5
                    for rate, (_, _, total) in zip(rates, series, strict=True)
                ]
            )
            style = series_style(index)
            ax.errorbar(
                sizes,
                rates,
                yerr=errors,
                marker=style["marker"],
                linestyle=style["linestyle"],
                color=style["color"],
                ecolor=style["color"],
                markersize=4,
                linewidth=1.0,
                elinewidth=0.9,
                capsize=2,
                label=label,
                zorder=2,
            )
        ax.set_xscale("log")
        ax.set_xlabel("datasets: chains (Potts) or sequences (HMM) per fit")
        ax.set_ylabel("fraction of 95% intervals covering truth")
        ax.legend(loc="lower right", frameon=False)
        fig.tight_layout()

    def _rate(entry: tuple[int, int, int]) -> str:
        size, hit, total = entry
        return f"{hit}/{total} = {hit / total:.3f} at {size}"

    caption = (
        f"Realized coverage of the 95 percent Wald intervals built from the "
        f"observed information, against the amount of data each fit sees. "
        f"Bars are binomial standard errors on the realized fraction. Both "
        f"instances converge on the nominal rate and neither sits on it at "
        f"the smallest sample, which is what an asymptotic approximation does "
        f"and a wrong formula does not. They approach from opposite sides. "
        f"The Potts chain over-covers and comes down: {_rate(potts[0])} "
        f"chains, {_rate(potts[-1])}. The hidden Markov model under-covers "
        f"and comes up: {_rate(hmm[0])} sequences, {_rate(hmm[-1])}. The "
        f"under-coverage has two identifiable sources absent from the Potts "
        f"chain -- some emission probabilities are fitted near zero, where a "
        f"Wald interval on the log scale is a poor approximation, and "
        f"aligning the hidden-state permutation to the truth is a "
        f"post-selection step that costs a little coverage. Seeds are fixed, "
        f"so every point is reproducible rather than redrawn."
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
    parser.add_argument("--potts-params", type=Path, required=True)
    parser.add_argument("--hmm-params", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)

    potts_params = load_potts_params(args.potts_params)
    hmm_params = load_hmm_params(args.hmm_params)

    potts = [
        (size, *potts_coverage(potts_params, size, replicates))
        for size, replicates in POTTS_SIZES
    ]
    hmm = [
        (size, *hmm_coverage(hmm_params, size, replicates))
        for size, replicates in HMM_SIZES
    ]

    fig, caption = build_figure(potts, hmm)
    try:
        return write_qa_figure(args.output_dir, "opt_coverage", fig, caption)
    finally:
        plt.close(fig)


if __name__ == "__main__":
    main()
