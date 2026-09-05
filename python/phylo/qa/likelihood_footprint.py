"""QA table: the memory footprint of a likelihood evaluation, against the
declared scale.

``ROADMAP.md`` §1.2 bounds the footprint to ``O(n x L x k)`` inside 16 GB
unified memory or 24 GB VRAM, and ``STATUS.md`` recorded that row as **Not
measured**. This table measures it.

**Why measured rather than derived.** The bound is a statement about what the
evaluator allocates, and an arithmetic model of that is a restatement of the
code rather than a check on it -- the 140 MB the Rust backend held live until
issue #232 was `O(n x L x k)` by the same arithmetic and six times what the
NumPy oracle needs. What settles the question is the allocator's own count.

**Why a caterpillar, and why not a drawn tree.** Pruning holds a partial
likelihood per *open* node, so its footprint is set by the topology's depth
rather than by its taxa. A caterpillar is the deepest tree on `n` leaves, so
it is the worst case and the one a *requirement* is about -- and it is the
shape at which the roadmap's `O(n x L x k)` is tight rather than loose. It is
also the only choice that keeps the table admissible: a drawn topology makes
the evaluator's peak depend on which tree the generator produced, and
perturbing the site count by one then moved the printed figure by 65%, which
``docs/CLAUDE.md`` forbids outright.

**Why the printed numbers are stable.** ``docs/CLAUDE.md`` admits only a
quantity continuous in its inputs, because CI byte-compares the rebuilt
artifact. A ``tracemalloc`` peak over a fixed topology is continuous in the
problem size and deterministic for a given interpreter and NumPy build, but
its last digits are not portable, so every figure is rounded to three
significant digits and the projection to two. Perturbing the site count by one
leaves the printed table unchanged, and
``tests/regression/qa/test_likelihood_footprint.py`` asserts it.

Wall clock is deliberately absent: ``DEV.md`` forbids ranking performance on
CI hardware, so timings live in ``tests/benchmarks`` instead.
"""

from __future__ import annotations

import tracemalloc

import numpy as np

from phylo.likelihood import pruning
from phylo.qa.figure import QATable, latex_integer
from phylo.qa.runner import table_main
from phylo.search.rl import with_uniform_branch_lengths
from phylo.search.topology import Topology
from phylo.sim.simulate import simulate_alignment
from phylo.sim.tree import Node

#: The declared scale's lower and middle reaches. The upper corner
#: (``n = 1000``) is projected rather than measured: rendering it on every
#: documentation build would cost a gigabyte for a number the linear fit
#: already supplies, and ``tests/regression/qa/test_likelihood_footprint.py``
#: is where the linearity that licenses the projection is asserted.
MEASURED_SIZES: tuple[tuple[int, int], ...] = ((20, 2_000), (20, 11_000), (100, 11_000))

#: The upper corner of ``ROADMAP.md`` §1.2's declared scale.
DECLARED_MAXIMUM: tuple[int, int] = (1_000, 11_000)

#: The tighter of the two hardware bounds in ``ROADMAP.md`` §1.2 (16 GB
#: unified memory against 24 GB VRAM), so the headroom reported is the one
#: that binds.
MEMORY_BUDGET_BYTES: int = 16 * 1024**3

#: States in the alphabet every measurement here runs at.
N_STATES: int = 4


def _round_significant(value: float, digits: int) -> float:
    """Round to ``digits`` significant figures, so the printed table is stable.

    Parameters
    ----------
    value : float
        The quantity to round.
    digits : int
        Significant figures to keep.

    Returns
    -------
    float
        ``value`` rounded, or ``0.0`` where it already is.
    """
    if value == 0.0:
        return 0.0
    exponent = int(np.floor(np.log10(abs(value))))
    return float(round(value, digits - 1 - exponent))


def caterpillar(n_taxa: int) -> Topology:
    """The deepest unrooted topology on ``n_taxa`` leaves, branch lengths unset.

    Every internal node has one leaf and one internal child, so the post-order
    depth is ``n_taxa - 2`` and pruning holds that many partials at once. That
    is the worst case the requirement has to hold at, and it is deterministic,
    which a drawn topology is not.

    Parameters
    ----------
    n_taxa : int
        Leaf count, at least 3.

    Returns
    -------
    Topology
        A caterpillar rooted at a trifurcation, as
        ``phylo.search.topology`` represents an unrooted tree.
    """
    leaves = [Node(name=f"t{index}", branch_length=None) for index in range(n_taxa)]
    tail: Node = leaves[-1]
    for leaf in reversed(leaves[2:-1]):
        tail = Node(name="i", branch_length=None, children=(leaf, tail))
    return Node(name="root", branch_length=None, children=(leaves[0], leaves[1], tail))


def measure(n_taxa: int, n_sites: int) -> tuple[float, float]:
    """Peak bytes held while simulating an alignment, and while evaluating it.

    The two are reported apart because they answer different questions: the
    first is what the *data* costs at this size, which no evaluator can avoid,
    and the second is what the algorithm adds on top of it. The topology is a
    caterpillar, so the second is the worst case rather than a draw.

    Parameters
    ----------
    n_taxa : int
        Leaf count.
    n_sites : int
        Sites per leaf.

    Returns
    -------
    tuple[float, float]
        Peak simulation bytes and peak evaluation bytes.
    """
    tau = with_uniform_branch_lengths(caterpillar(n_taxa), 0.1)
    pi = np.full(N_STATES, 1.0 / N_STATES)

    tracemalloc.start()
    dataset = simulate_alignment(tau=tau, k=N_STATES, pi=pi, seed=1, n_sites=n_sites)
    _, simulate_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    alignment = dict(dataset.alignment)
    tracemalloc.start()
    pruning.log_likelihood(tau, N_STATES, pi, alignment)
    _, evaluate_peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return float(simulate_peak), float(evaluate_peak)


def warm_up() -> None:
    """Discard one measurement, so the next is a property of the problem size.

    The first simulation in a process pays NumPy's own one-time allocations
    and ``tracemalloc`` counts them: measured cold, the smallest cell reads
    1.29 MB against 0.636 MB warm. That doubling has nothing to do with the
    problem size, and publishing it would put a figure in the table that moves
    with call order rather than with its inputs -- exactly what
    ``docs/CLAUDE.md`` refuses. Both this module and its regression tests call
    this first, so the fact has one home rather than two.
    """
    measure(*MEASURED_SIZES[0])


def bytes_per_site_taxon(
    sizes: tuple[tuple[int, int], ...], totals: list[float]
) -> float:
    """The single coefficient the ``O(n x L x k)`` claim reduces to.

    A least-squares slope through the origin, because the bound has no constant
    term: an evaluator with a fixed overhead would show as a systematically
    poor fit rather than being absorbed into an intercept.

    Both costs are linear in the taxon-site product at the topology measured --
    simulation because it holds every node's states, evaluation because a
    caterpillar's depth *is* its taxon count -- so one slope is a fit rather
    than a shape mismatch papered over.
    ``tests/regression/qa/test_likelihood_footprint.py`` asserts that linearity
    and that a shallower topology costs strictly less, which together are what
    make the projection a bound rather than an estimate.

    Parameters
    ----------
    sizes : tuple[tuple[int, int], ...]
        The ``(n_taxa, n_sites)`` pairs measured.
    totals : list[float]
        Peak bytes at each, in the same order.

    Returns
    -------
    float
        Bytes per taxon-site.
    """
    products = np.array([n_taxa * n_sites for n_taxa, n_sites in sizes], dtype=float)
    observed = np.asarray(totals, dtype=float)
    return float(products @ observed / (products @ products))


def render_footprint(
    rows: list[tuple[int, int, float, float]], coefficient: float
) -> str:
    """Build the LaTeX ``tabular``: one row per measured size, then the projection.

    Parameters
    ----------
    rows : list[tuple[int, int, float, float]]
        ``(n_taxa, n_sites, simulate_bytes, evaluate_bytes)`` per measured size.
    coefficient : float
        Bytes per taxon-site, from :func:`bytes_per_site_taxon`.

    Returns
    -------
    str
        A complete ``tabular`` environment.
    """
    body = [
        " & ".join(
            [
                latex_integer(n_taxa),
                latex_integer(n_sites),
                f"{_round_significant(simulate_bytes / 1e6, 3):g}",
                f"{_round_significant(evaluate_bytes / 1e6, 3):g}",
                f"{_round_significant((simulate_bytes + evaluate_bytes) / 1e6, 3):g}",
            ]
        )
        + r" \\"
        for n_taxa, n_sites, simulate_bytes, evaluate_bytes in rows
    ]
    projected_taxa, projected_sites = DECLARED_MAXIMUM
    projected = coefficient * projected_taxa * projected_sites
    projection = (
        " & ".join(
            [
                latex_integer(projected_taxa),
                latex_integer(projected_sites),
                r"\multicolumn{2}{c}{projected}",
                f"{_round_significant(projected / 1e6, 2):g}",
            ]
        )
        + r" \\"
    )
    return "\n".join(
        [
            r"\begin{tabular}{rrrrr}",
            r"  \toprule",
            r"  Taxa & Sites & Simulate (MB) & Evaluate (MB) & Total (MB) \\",
            r"  \midrule",
            *(f"  {row}" for row in body),
            r"  \midrule",
            f"  {projection}",
            r"  \bottomrule",
            r"\end{tabular}",
        ]
    )


def build_caption(coefficient: float) -> str:
    """Caption text for the footprint table.

    Parameters
    ----------
    coefficient : float
        Bytes per taxon-site.

    Returns
    -------
    str
        Plain-text caption, safe to ``\\input`` into LaTeX verbatim.
    """
    projected_taxa, projected_sites = DECLARED_MAXIMUM
    projected = coefficient * projected_taxa * projected_sites
    headroom = MEMORY_BUDGET_BYTES / projected
    return (
        "Peak memory held while simulating a Jukes-Cantor alignment and while "
        f"evaluating its likelihood by pruning, at {N_STATES} states, over "
        "three points of the declared scale, counted by tracemalloc. The "
        f"fitted cost is {_round_significant(coefficient, 3):g} bytes per "
        "taxon-site with no constant term, from which the last row projects "
        f"the declared maximum of {latex_integer(projected_taxa)} taxa and "
        f"{latex_integer(projected_sites)} sites. That projection sits a "
        f"factor of {_round_significant(headroom, 2):g} inside the 16 GB "
        "unified-memory requirement. The topology is a caterpillar at every "
        "size, which is the deepest tree on its leaves and so the worst case "
        "for an evaluator holding one partial likelihood per open node: a "
        "balanced tree of the same taxon count costs strictly less. Every "
        "figure is rounded so the printed table does not move with the "
        "allocator's last digits; timings are reported in the benchmark suite "
        "instead, because a wall clock ranks the machine rather than the code."
    )


def build_table() -> tuple[str, str]:
    """Measure every size and assemble the ``tabular`` body and its caption.

    Returns
    -------
    tuple[str, str]
        The ``tabular`` body and the caption.
    """
    warm_up()

    rows: list[tuple[int, int, float, float]] = []
    totals: list[float] = []
    for n_taxa, n_sites in MEASURED_SIZES:
        simulate_bytes, evaluate_bytes = measure(n_taxa, n_sites)
        rows.append((n_taxa, n_sites, simulate_bytes, evaluate_bytes))
        totals.append(simulate_bytes + evaluate_bytes)
    coefficient = bytes_per_site_taxon(MEASURED_SIZES, totals)
    return render_footprint(rows, coefficient), build_caption(coefficient)


def main(argv: list[str] | None = None) -> QATable:
    """Render the footprint table.

    Parameters
    ----------
    argv : list[str] | None
        Argument vector; ``None`` reads ``sys.argv``.

    Returns
    -------
    QATable
        Paths written, and the caption.
    """
    return table_main(
        stem="likelihood_footprint",
        description=__doc__,
        params=(),
        build=build_table,
        argv=argv,
    )


if __name__ == "__main__":
    main()
