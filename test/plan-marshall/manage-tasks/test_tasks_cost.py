#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for deterministic task cost-sizing (_tasks_cost.py)."""


import pytest
from _tasks_cost_fixtures import (
    _L_MAX,
    _M_MAX,
    _PROFILE_WEIGHT_DEFAULT,
    _S_MAX,
    _XL_MAX,
    _XS_MAX,
    COST_SIZES,
    PROFILE_WEIGHTS,
    W_PROFILE,
    W_SKILLS,
    W_STEP,
    W_TARGET_FILES,
    compute_score,
    profile_weight,
    score_to_size,
)

# =============================================================================
# profile_weight
# =============================================================================


def test_profile_weight_implementation():
    """implementation profile takes its rubric weight."""
    assert profile_weight('implementation') == PROFILE_WEIGHTS['implementation']


def test_profile_weight_module_testing():
    """module_testing profile takes its rubric weight."""
    assert profile_weight('module_testing') == PROFILE_WEIGHTS['module_testing']


def test_profile_weight_verification_is_lightest():
    """verification profile is the lightest of the three known profiles."""
    assert profile_weight('verification') == PROFILE_WEIGHTS['verification']
    assert profile_weight('verification') < profile_weight('implementation')
    assert profile_weight('verification') < profile_weight('module_testing')


def test_profile_weight_unknown_takes_default():
    """An unknown profile takes the middle default weight."""
    assert profile_weight('architecture') == _PROFILE_WEIGHT_DEFAULT


def test_profile_weight_none_takes_default():
    """A None profile takes the middle default weight."""
    assert profile_weight(None) == _PROFILE_WEIGHT_DEFAULT


# =============================================================================
# compute_score — weighting (rubric § 1)
# =============================================================================


def test_compute_score_matches_weighted_sum():
    """Score is the exact weighted sum of the four signals."""
    expected = (
        (W_STEP * 4)
        + (W_PROFILE * profile_weight('implementation'))
        + (W_SKILLS * 2)
        + (W_TARGET_FILES * 3)
    )
    assert compute_score(4, 'implementation', 2, 3) == expected


def test_compute_score_step_count_is_dominant():
    """One extra step outweighs one extra skill or one extra target file.

    Pins the rubric § 1 'step_count is dominant' invariant: W_STEP exceeds
    both W_SKILLS and W_TARGET_FILES.
    """
    base = compute_score(3, 'implementation', 1, 1)
    one_more_step = compute_score(4, 'implementation', 1, 1)
    one_more_skill = compute_score(3, 'implementation', 2, 1)
    one_more_file = compute_score(3, 'implementation', 1, 2)

    assert (one_more_step - base) == W_STEP
    assert (one_more_step - base) > (one_more_skill - base)
    assert (one_more_step - base) > (one_more_file - base)


def test_compute_score_monotone_in_step_count():
    """Increasing step_count can only raise the score."""
    assert compute_score(5, 'implementation', 1, 1) > compute_score(4, 'implementation', 1, 1)


def test_compute_score_monotone_in_skills_count():
    """Increasing skills_count can only raise the score."""
    assert compute_score(3, 'implementation', 3, 1) > compute_score(3, 'implementation', 2, 1)


def test_compute_score_monotone_in_target_file_count():
    """Increasing target_file_count can only raise the score."""
    assert compute_score(3, 'implementation', 1, 4) > compute_score(3, 'implementation', 1, 3)


def test_compute_score_zero_signals():
    """All-zero counts reduce the score to the profile term alone."""
    assert compute_score(0, 'verification', 0, 0) == W_PROFILE * profile_weight('verification')


def test_compute_score_rejects_negative_step_count():
    """A negative step_count raises ValueError."""
    with pytest.raises(ValueError, match='step_count'):
        compute_score(-1, 'implementation', 0, 0)


def test_compute_score_rejects_negative_skills_count():
    """A negative skills_count raises ValueError."""
    with pytest.raises(ValueError, match='skills_count'):
        compute_score(1, 'implementation', -1, 0)


def test_compute_score_rejects_negative_target_file_count():
    """A negative target_file_count raises ValueError."""
    with pytest.raises(ValueError, match='target_file_count'):
        compute_score(1, 'implementation', 0, -1)


# =============================================================================
# score_to_size — band mapping (rubric § 2)
# =============================================================================


def test_score_to_size_below_xs_max_is_xs():
    """A score just below the XS/S boundary maps to XS."""
    assert score_to_size(_XS_MAX - 1) == 'XS'


def test_score_to_size_at_xs_max_is_s():
    """A score exactly at the XS/S boundary maps to S (band is [_XS_MAX, _S_MAX))."""
    assert score_to_size(_XS_MAX) == 'S'


def test_score_to_size_below_s_max_is_s():
    """A score just below the S/M boundary maps to S."""
    assert score_to_size(_S_MAX - 1) == 'S'


def test_score_to_size_at_s_max_is_m():
    """A score exactly at the S/M boundary maps to M (band is [_S_MAX, _M_MAX))."""
    assert score_to_size(_S_MAX) == 'M'


def test_score_to_size_below_m_max_is_m():
    """A score just below the M/L boundary maps to M."""
    assert score_to_size(_M_MAX - 1) == 'M'


def test_score_to_size_at_m_max_is_l():
    """A score exactly at the M/L boundary maps to L."""
    assert score_to_size(_M_MAX) == 'L'


def test_score_to_size_below_l_max_is_l():
    """A score just below the L/XL boundary maps to L."""
    assert score_to_size(_L_MAX - 1) == 'L'


def test_score_to_size_at_l_max_is_xl():
    """A score exactly at the L/XL boundary maps to XL."""
    assert score_to_size(_L_MAX) == 'XL'


def test_score_to_size_below_xl_max_is_xl():
    """A score just below the XL/XXL boundary maps to XL."""
    assert score_to_size(_XL_MAX - 1) == 'XL'


def test_score_to_size_at_xl_max_is_xxl():
    """A score exactly at the XL/XXL boundary maps to XXL."""
    assert score_to_size(_XL_MAX) == 'XXL'


def test_score_to_size_zero_is_smallest():
    """A zero score maps to the smallest size (XS)."""
    assert score_to_size(0) == 'XS'


def test_score_to_size_very_large_is_xxl():
    """A very large score maps to the largest size (XXL)."""
    assert score_to_size(_XL_MAX * 10) == 'XXL'


def test_score_to_size_is_monotone_non_decreasing():
    """The band mapping never assigns a smaller size to a larger score."""
    order = {label: i for i, label in enumerate(COST_SIZES)}
    prev = -1
    for score in range(0, _XL_MAX + 50):
        rank = order[score_to_size(score)]
        assert rank >= prev
        prev = rank
