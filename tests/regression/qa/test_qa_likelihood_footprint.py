"""The memory footprint table's structural claims, checked against measurement
rather than against the arithmetic that produced the table.

``ROADMAP.md`` §1.2 bounds the footprint to ``O(n x L x k)``.
`phylo.qa.likelihood_footprint` measures three points of the declared scale and
projects the fourth, and that projection is usable only if three things hold:
both costs are linear in the taxon-site product at the topology measured, the
topology measured is the worst case, and the printed table does not move when
its inputs are perturbed.

Byte counts are not pinned. They move with the interpreter and the NumPy
build, and a test asserting one would fail for the machine rather than for the
code -- the same reason ``DEV.md`` keeps wall clocks out of CI assertions. The
*shapes* of the two curves are what the projection rests on, and those are
properties of the algorithms.
"""

from __future__ import annotations

from itertools import pairwise

import numpy as np
import pytest
from phylo.qa import likelihood_footprint
from phylo.qa.likelihood_footprint import (
    DECLARED_MAXIMUM,
    MEMORY_BUDGET_BYTES,
    bytes_per_site_taxon,
    caterpillar,
    measure,
    warm_up,
)
from phylo.search.rl import with_uniform_branch_lengths
from phylo.sim.tree import Node

# Small enough that the whole file runs in seconds: every claim here is about
# a curve's shape, and a shape is visible at any sizes spanning a factor.
FIXED_TAXA = 16
FIXED_SITES = 2_000
SITES_AT_FIXED_TAXA = (2_000, 4_000, 8_000)
TAXA_AT_FIXED_SITES = (16, 32, 64)


@pytest.fixture(autouse=True, scope="module")
def _warmed() -> None:
    """Absorb the cold-call inflation before any assertion reads a peak.

    `phylo.qa.likelihood_footprint.warm_up` states why; calling it from here
    rather than restating the reason keeps one home for the fact.
    """
    warm_up()


def _balanced(n_taxa: int) -> Node:
    """A balanced binary topology on ``n_taxa`` leaves, a power of two.

    The shallow counterpart of `caterpillar`: depth ``log2(n_taxa)`` against
    ``n_taxa - 2``, which is what makes it the cheaper case for an evaluator
    holding one partial per open node.
    """
    level: list[Node] = [
        Node(name=f"t{index}", branch_length=None) for index in range(n_taxa)
    ]
    while len(level) > 3:
        level = [
            Node(name="i", branch_length=None, children=(left, right))
            for left, right in zip(level[::2], level[1::2], strict=True)
        ]
    return Node(name="root", branch_length=None, children=tuple(level))


def test_simulation_memory_is_linear_in_the_taxon_site_product() -> None:
    """Doubling either taxa or sites doubles what simulation holds.

    The simulator keeps every node's states, so the cost is `2n x L x 8` bytes
    and each doubling multiplies it by 2. A simulator that kept only the
    leaves, or that left a per-site temporary alive, would break this in
    opposite directions.
    """
    at_sites = [measure(FIXED_TAXA, sites)[0] for sites in SITES_AT_FIXED_TAXA]
    for smaller, larger in pairwise(at_sites):
        assert larger / smaller == pytest.approx(2.0, rel=0.05)

    at_taxa = [measure(taxa, FIXED_SITES)[0] for taxa in TAXA_AT_FIXED_SITES]
    for smaller, larger in pairwise(at_taxa):
        assert larger / smaller == pytest.approx(2.0, rel=0.10)


def test_evaluation_memory_is_linear_in_the_taxon_site_product_on_a_caterpillar() -> (
    None
):
    """A caterpillar's depth is its taxon count, so the evaluator is linear too.

    Pruning holds one partial likelihood per *open* node, and on the deepest
    tree every node is open at once. That is what makes ``O(n x L x k)`` tight
    at this topology rather than loose, and it is why the table's single fitted
    slope is a fit rather than a shape mismatch papered over.
    """
    at_sites = [measure(FIXED_TAXA, sites)[1] for sites in SITES_AT_FIXED_TAXA]
    for smaller, larger in pairwise(at_sites):
        assert larger / smaller == pytest.approx(2.0, rel=0.05)

    at_taxa = [measure(taxa, FIXED_SITES)[1] for taxa in TAXA_AT_FIXED_SITES]
    for smaller, larger in pairwise(at_taxa):
        assert larger / smaller == pytest.approx(2.0, rel=0.10)


def test_a_balanced_topology_costs_strictly_less_than_the_caterpillar() -> None:
    """The table reports the worst case, and this is what says so.

    Same taxa, same sites, same data volume: only the depth differs. If a
    balanced tree were not cheaper, the caterpillar would not be the bound the
    caption claims, and the projection would understate the requirement.
    """
    import tracemalloc

    from phylo.likelihood import pruning
    from phylo.sim.simulate import simulate_alignment

    pi = np.full(4, 0.25)
    peaks: list[float] = []
    for topology in (_balanced(FIXED_TAXA), caterpillar(FIXED_TAXA)):
        tau = with_uniform_branch_lengths(topology, 0.1)
        alignment = dict(
            simulate_alignment(
                tau=tau, k=4, pi=pi, seed=1, n_sites=FIXED_SITES
            ).alignment
        )
        tracemalloc.start()
        pruning.log_likelihood(tau, 4, pi, alignment)
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        peaks.append(float(peak))

    balanced_peak, caterpillar_peak = peaks
    assert balanced_peak < caterpillar_peak


def test_the_declared_maximum_is_projected_inside_the_memory_requirement() -> None:
    """The bound `ROADMAP.md` states, evaluated at the corner it states it for.

    Measured at three points, fitted through the origin, and projected to 1000
    taxa by 11,000 sites. The assertion is an order of magnitude of headroom
    rather than an exact figure, because the byte count is not portable and the
    margin is what the requirement is about.
    """
    sizes = ((16, 2_000), (16, 4_000), (32, 4_000))
    totals = [sum(measure(taxa, sites)) for taxa, sites in sizes]
    coefficient = bytes_per_site_taxon(sizes, totals)

    projected = coefficient * DECLARED_MAXIMUM[0] * DECLARED_MAXIMUM[1]
    assert projected < MEMORY_BUDGET_BYTES / 10


def test_the_printed_table_does_not_move_when_its_inputs_are_perturbed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`docs/CLAUDE.md`'s admissibility check, run rather than asserted in prose.

    Only a quantity continuous in its inputs may be published, because CI
    byte-compares the rebuilt artifact. One extra site must leave every
    measured figure and the whole caption alone. An earlier draft drew the
    topology from the site count, and this moved the evaluator column by 65%.
    """
    sizes = ((16, 2_000), (16, 4_000))
    monkeypatch.setattr(likelihood_footprint, "MEASURED_SIZES", sizes)
    _, baseline_caption = likelihood_footprint.build_table()

    perturbed = tuple((taxa, sites + 1) for taxa, sites in sizes)
    monkeypatch.setattr(likelihood_footprint, "MEASURED_SIZES", perturbed)
    _, perturbed_caption = likelihood_footprint.build_table()

    assert perturbed_caption == baseline_caption


def test_the_linearity_check_would_fail_on_a_quadratic_curve() -> None:
    """The fit rejects the shape it exists to reject.

    `bytes_per_site_taxon` fits through the origin, so a cost quadratic in the
    product -- an evaluator materializing a per-node-pair array, say -- leaves
    a residual the fit cannot absorb. Asserting that here is what says the
    tests above measure the curve and not merely the largest point.
    """
    sizes = ((16, 2_000), (16, 4_000), (32, 4_000))
    products = np.array([taxa * sites for taxa, sites in sizes], dtype=float)

    linear = list(products * 32.0)
    quadratic = list(products**2 * 1e-4)

    assert np.allclose(
        products * bytes_per_site_taxon(sizes, linear), linear, rtol=1e-12
    )
    assert not np.allclose(
        products * bytes_per_site_taxon(sizes, quadratic), quadratic, rtol=0.1
    )
