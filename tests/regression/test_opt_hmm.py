"""Regression tests for the discrete-HMM reference instance.

The forward recursion is checked against brute-force enumeration over every
hidden path -- the same independent-oracle pattern
``phylo.likelihood.brute_force`` establishes for pruning, and for the same
reason: a recursion checked only against itself is checked against nothing.
``opt/CLAUDE.md``'s finite-difference derivative check is here too.
"""

from __future__ import annotations

from itertools import permutations, product
from pathlib import Path

import numpy as np
import pytest
import torch
from numpy.testing import assert_allclose
from phylo.opt.hmm import (
    HmmObjective,
    forward_log_likelihood,
    load_hmm_params,
    simulate_sequences,
)

from tests._fixtures import FIXTURES_DIR
from tests._objective_checks import assert_gradient_matches_finite_differences

FIXTURE = FIXTURES_DIR / "hmm_params.yaml"

# Relative throughout: the log-likelihood is a sum over sequences and sites
# (`DEV.md`, issue #111).
_RTOL_ORACLE = 1e-12
_RTOL_GRADIENT = 1e-6
_FINITE_DIFFERENCE_STEP = 1e-5

# Brute force is O(n_states ** length); 3 ** 7 = 2187 paths per sequence is
# the largest that stays a fast test, and the recursion is length-agnostic,
# so a longer chain would not exercise anything new.
_BRUTE_FORCE_SEQUENCES = 3
_BRUTE_FORCE_LENGTH = 7


def _brute_force_log_likelihood(
    observations: torch.Tensor,
    log_initial: torch.Tensor,
    log_transition: torch.Tensor,
    log_emission: torch.Tensor,
) -> float:
    """Sum over every hidden path, with no message passing anywhere."""
    n_states, length = log_initial.shape[0], observations.shape[1]
    total = 0.0
    for row in observations:
        weights = [
            log_initial[path[0]]
            + sum(log_transition[path[t], path[t + 1]] for t in range(length - 1))
            + sum(log_emission[path[t], row[t]] for t in range(length))
            for path in product(range(n_states), repeat=length)
        ]
        total += float(torch.logsumexp(torch.stack(weights), dim=0))
    return total


def _log_truth(params: object) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    return tuple(  # type: ignore[return-value]
        torch.log(torch.as_tensor(part, dtype=torch.float64))
        for part in (
            params.initial,  # type: ignore[attr-defined]
            params.transition,  # type: ignore[attr-defined]
            params.emission,  # type: ignore[attr-defined]
        )
    )


def test_forward_matches_brute_force_path_enumeration() -> None:
    params = load_hmm_params(FIXTURE)
    observations = torch.as_tensor(
        simulate_sequences(params)[:_BRUTE_FORCE_SEQUENCES, :_BRUTE_FORCE_LENGTH]
    )
    log_initial, log_transition, log_emission = _log_truth(params)

    expected = _brute_force_log_likelihood(
        observations, log_initial, log_transition, log_emission
    )
    actual = forward_log_likelihood(
        observations, log_initial, log_transition, log_emission
    )
    assert_allclose(float(actual), expected, rtol=_RTOL_ORACLE)


def test_the_likelihood_is_invariant_to_relabelling_the_hidden_states() -> None:
    # The identifiability caveat, asserted rather than only documented: a
    # recovery test that compared parameters without aligning the
    # permutation would fail on a correct fit.
    params = load_hmm_params(FIXTURE)
    observations = torch.as_tensor(simulate_sequences(params)[:20])
    log_initial, log_transition, log_emission = _log_truth(params)
    reference = float(
        forward_log_likelihood(observations, log_initial, log_transition, log_emission)
    )

    for order in permutations(range(params.n_states)):
        index = torch.as_tensor(order)
        permuted = float(
            forward_log_likelihood(
                observations,
                log_initial[index],
                log_transition[index][:, index],
                log_emission[index],
            )
        )
        assert_allclose(permuted, reference, rtol=_RTOL_ORACLE)


@pytest.mark.parametrize("at_truth", [True, False])
def test_gradient_matches_central_finite_differences(at_truth: bool) -> None:
    params = load_hmm_params(FIXTURE)
    # A short slice: the finite-difference check costs two objective
    # evaluations per parameter, and the recursion it exercises is the same
    # at any length.
    objective = HmmObjective(
        simulate_sequences(params)[:40], params.n_states, params.n_symbols
    )
    theta = (
        objective.theta_from_truth(params.initial, params.transition, params.emission)
        if at_truth
        else objective.initial()
    )

    assert_gradient_matches_finite_differences(
        objective, theta, _FINITE_DIFFERENCE_STEP, _RTOL_GRADIENT
    )


def test_theta_round_trips_through_the_constraint_map() -> None:
    params = load_hmm_params(FIXTURE)
    objective = HmmObjective(
        simulate_sequences(params), params.n_states, params.n_symbols
    )
    constrained = objective.constrain(
        objective.theta_from_truth(params.initial, params.transition, params.emission)
    )
    assert_allclose(
        torch.exp(constrained["log_initial"]).numpy(), params.initial, rtol=1e-13
    )
    assert_allclose(
        torch.exp(constrained["log_transition"]).numpy(), params.transition, rtol=1e-13
    )
    assert_allclose(
        torch.exp(constrained["log_emission"]).numpy(), params.emission, rtol=1e-13
    )


def test_theta_has_one_entry_per_free_probability() -> None:
    # 2 free initial + 3 rows x 2 free transition + 3 rows x 3 free emission.
    objective = HmmObjective(np.zeros((2, 5), dtype=np.int64), n_states=3, n_symbols=4)
    assert objective.n_parameters == 17
    assert objective.initial().shape == (17,)


def test_the_initial_point_is_uniform_everywhere() -> None:
    objective = HmmObjective(np.zeros((2, 5), dtype=np.int64), n_states=3, n_symbols=4)
    constrained = objective.constrain(objective.initial())
    assert_allclose(
        torch.exp(constrained["log_initial"]).numpy(), np.full(3, 1 / 3), rtol=1e-14
    )
    assert_allclose(
        torch.exp(constrained["log_transition"]).numpy(),
        np.full((3, 3), 1 / 3),
        rtol=1e-14,
    )
    assert_allclose(
        torch.exp(constrained["log_emission"]).numpy(),
        np.full((3, 4), 0.25),
        rtol=1e-14,
    )


def test_simulated_sequences_have_the_declared_shape_and_alphabet() -> None:
    params = load_hmm_params(FIXTURE)
    observations = simulate_sequences(params)
    assert observations.shape == (params.n_sequences, params.sequence_length)
    assert set(np.unique(observations)) <= set(range(params.n_symbols))


def test_simulation_is_reproducible_from_the_seed() -> None:
    params = load_hmm_params(FIXTURE)
    assert np.array_equal(simulate_sequences(params), simulate_sequences(params))


def test_simulated_symbol_frequencies_match_the_analytic_marginal() -> None:
    # The stationary-free marginal is exact: average the emission rows over
    # the hidden-state distribution at each step, which is the initial
    # distribution pushed through the transition matrix. Computed in closed
    # form, so this pins the simulator against the model rather than against
    # a second simulation.
    params = load_hmm_params(FIXTURE)
    observations = simulate_sequences(params)

    state = params.initial
    expected = np.zeros(params.n_symbols)
    for _ in range(params.sequence_length):
        expected += state @ params.emission
        state = state @ params.transition
    expected /= params.sequence_length

    observed = (
        np.bincount(observations.ravel(), minlength=params.n_symbols)
        / observations.size
    )
    # Monte Carlo standard error at 4500 draws is ~0.007 for p near 0.3;
    # 0.02 is under three of those.
    assert_allclose(observed, expected, atol=0.02)


@pytest.mark.parametrize(
    ("replace", "with_", "message"),
    [
        ("n_states: 3", "n_states: 1", "n_states must be >= 2"),
        ("n_symbols: 4", "n_symbols: 1", "n_symbols must be >= 2"),
        ("sequence_length: 15", "sequence_length: 1", "sequence_length must be >= 2"),
        ("initial: [0.5, 0.3, 0.2]", "initial: [0.5, 0.3]", "initial has shape"),
        ("initial: [0.5, 0.3, 0.2]", "initial: [0.5, 0.3, 0.9]", "initial rows sum to"),
    ],
)
def test_a_malformed_fixture_is_refused(
    replace: str, with_: str, message: str, tmp_path: Path
) -> None:
    path = tmp_path / "hmm.yaml"
    path.write_text(FIXTURE.read_text().replace(replace, with_))
    with pytest.raises(ValueError, match=message):
        load_hmm_params(path)


def test_a_missing_field_is_refused(tmp_path: Path) -> None:
    text = "\n".join(
        line
        for line in FIXTURE.read_text().splitlines()
        if not line.startswith("seed:")
    )
    path = tmp_path / "hmm.yaml"
    path.write_text(text)
    with pytest.raises(ValueError, match="missing required field"):
        load_hmm_params(path)
