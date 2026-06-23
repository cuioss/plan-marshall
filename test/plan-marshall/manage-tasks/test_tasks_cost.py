#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for deterministic task cost-sizing (_tasks_cost.py).

The pure deriver in ``_tasks_cost.py`` IMPLEMENTS the rubric defined in
``marketplace/bundles/plan-marshall/skills/phase-4-plan/standards/cost-sizing.md``.
These tests pin the four-signal weighted score, the score→size band mapping,
the size→token table, the public ``derive_cost_size`` entry point, and the
``derive-cost-size`` CLI subcommand integration via ``manage-tasks``.

Per the task contract, the canonical thresholds are NOT inline-copied as bare
magic numbers into assertions: each boundary test references the rubric weights
imported from the module under test (``W_STEP`` / ``W_PROFILE`` / ``W_SKILLS`` /
``W_TARGET_FILES`` / ``_S_MAX`` / ``_M_MAX`` / ``_L_MAX``), so the assertions
track the single source of truth in ``cost-sizing.md`` rather than duplicating
it. The rubric's band semantics (S ``< 60``, M ``[60,150)``, L ``[150,300)``,
XL ``>= 300``) are exercised at and around each band boundary.

Tier 2 (direct import) tests for the pure functions, plus Tier 3 subprocess
tests for the ``derive-cost-size`` CLI plumbing.
"""

import pytest

from conftest import get_script_path, load_script_module, run_script

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-tasks', 'manage-tasks.py')

_cost = load_script_module('plan-marshall', 'manage-tasks', '_tasks_cost.py', '_tasks_cost_under_test')

profile_weight = _cost.profile_weight
compute_score = _cost.compute_score
score_to_size = _cost.score_to_size
resolve_size_table = _cost.resolve_size_table
derive_cost_size = _cost.derive_cost_size

W_STEP = _cost.W_STEP
W_PROFILE = _cost.W_PROFILE
W_SKILLS = _cost.W_SKILLS
W_TARGET_FILES = _cost.W_TARGET_FILES
PROFILE_WEIGHTS = _cost.PROFILE_WEIGHTS
_PROFILE_WEIGHT_DEFAULT = _cost._PROFILE_WEIGHT_DEFAULT
_S_MAX = _cost._S_MAX
_M_MAX = _cost._M_MAX
_L_MAX = _cost._L_MAX
COST_SIZES = _cost.COST_SIZES
DEFAULT_SIZE_TABLE = _cost.DEFAULT_SIZE_TABLE


def _score_only(step_count, profile, skills_count, target_file_count):
    """Recompute the rubric weighted-sum from the imported weights.

    Used to derive boundary signal combinations for the band tests without
    hard-coding raw score literals — the weights come from the module under
    test, which mirrors the rubric § 1 weighting table.
    """
    return (
        (W_STEP * step_count)
        + (W_PROFILE * profile_weight(profile))
        + (W_SKILLS * skills_count)
        + (W_TARGET_FILES * target_file_count)
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


def test_score_to_size_zero_is_smallest():
    """A zero score maps to the smallest size."""
    assert score_to_size(0) == 'S'


def test_score_to_size_very_large_is_xl():
    """A very large score maps to XL."""
    assert score_to_size(_L_MAX * 10) == 'XL'


def test_score_to_size_is_monotone_non_decreasing():
    """The band mapping never assigns a smaller size to a larger score."""
    order = {label: i for i, label in enumerate(COST_SIZES)}
    prev = -1
    for score in range(0, _L_MAX + 50):
        rank = order[score_to_size(score)]
        assert rank >= prev
        prev = rank


# =============================================================================
# resolve_size_table
# =============================================================================


def test_resolve_size_table_default_parses_magnitudes():
    """The default table parses every magnitude string to an int."""
    table = resolve_size_table(None)
    assert set(table) == set(COST_SIZES)
    assert all(isinstance(v, int) for v in table.values())


def test_resolve_size_table_default_matches_rubric_defaults():
    """The default resolved table matches the parsed DEFAULT_SIZE_TABLE."""
    table = resolve_size_table(None)
    assert table['S'] == 25_000
    assert table['M'] == 60_000
    assert table['L'] == 130_000
    assert table['XL'] == 260_000


def test_resolve_size_table_default_is_monotone():
    """Larger sizes map to larger token magnitudes."""
    table = resolve_size_table(None)
    assert table['S'] < table['M'] < table['L'] < table['XL']


def test_resolve_size_table_accepts_injected_table():
    """A caller-injected table overrides the default and is parsed."""
    injected = {'S': '1K', 'M': '2K', 'L': '3K', 'XL': '4K'}
    table = resolve_size_table(injected)
    assert table == {'S': 1000, 'M': 2000, 'L': 3000, 'XL': 4000}


def test_resolve_size_table_accepts_int_values():
    """A table with plain int values resolves unchanged."""
    injected = {'S': 1, 'M': 2, 'L': 3, 'XL': 4}
    table = resolve_size_table(injected)
    assert table == {'S': 1, 'M': 2, 'L': 3, 'XL': 4}


def test_resolve_size_table_rejects_missing_key():
    """A table missing a required size key raises ValueError."""
    with pytest.raises(ValueError, match='XL'):
        resolve_size_table({'S': '1K', 'M': '2K', 'L': '3K'})


# =============================================================================
# derive_cost_size — public entry point
# =============================================================================


def test_derive_cost_size_returns_size_and_tokens():
    """The deriver returns a (size, tokens) tuple for valid signals."""
    size, tokens = derive_cost_size(3, 'verification', 0, 2)
    assert size in COST_SIZES
    assert isinstance(tokens, int)


def test_derive_cost_size_tokens_track_default_table():
    """The returned token magnitude is the default table's value for the size."""
    size, tokens = derive_cost_size(3, 'verification', 0, 2)
    assert tokens == resolve_size_table(None)[size]


def test_derive_cost_size_honors_injected_table():
    """An injected size→token table drives the returned token magnitude."""
    injected = {'S': '7K', 'M': '8K', 'L': '9K', 'XL': '10K'}
    size, tokens = derive_cost_size(3, 'verification', 0, 2, size_table=injected)
    assert tokens == resolve_size_table(injected)[size]


def test_derive_cost_size_is_deterministic():
    """Identical signals always yield identical results."""
    a = derive_cost_size(14, 'implementation', 2, 6)
    b = derive_cost_size(14, 'implementation', 2, 6)
    assert a == b


def test_derive_cost_size_rejects_negative_count():
    """A negative count propagates the deriver's ValueError."""
    with pytest.raises(ValueError):
        derive_cost_size(-1, 'implementation', 0, 0)


def test_derive_cost_size_rejects_malformed_table():
    """A malformed size table propagates the deriver's ValueError."""
    with pytest.raises(ValueError):
        derive_cost_size(3, 'implementation', 0, 0, size_table={'S': '1K'})


# =============================================================================
# Worked examples (rubric § 4) — canonical cases the deriver MUST agree with
# =============================================================================


@pytest.mark.parametrize(
    'step_count,profile,skills,target_files,expected_size',
    [
        (5, 'verification', 1, 5, 'M'),       # 5-step documentation edit -> score 77
        (3, 'verification', 0, 2, 'S'),       # 3-step doc-only verify -> score 42
        (14, 'implementation', 2, 6, 'L'),    # 14-step config change -> score 182
        (55, 'module_testing', 3, 20, 'XL'),  # 55-step multi-file test refactor -> score 651
    ],
)
def test_derive_cost_size_worked_examples(step_count, profile, skills, target_files, expected_size):
    """Each rubric § 4 worked example resolves to its documented size.

    The expected sizes come from the rubric's worked-examples table; the score
    is recomputed from the imported weights (not hard-coded) and cross-checked.
    """
    score = _score_only(step_count, profile, skills, target_files)
    assert score_to_size(score) == expected_size

    size, _tokens = derive_cost_size(step_count, profile, skills, target_files)
    assert size == expected_size


# =============================================================================
# Subcommand integration via manage-tasks (Tier 3 — CLI plumbing)
# =============================================================================


def test_cli_derive_cost_size_returns_success():
    """The derive-cost-size subcommand returns a success TOON."""
    result = run_script(
        SCRIPT_PATH,
        'derive-cost-size',
        '--step-count', '3',
        '--profile', 'verification',
        '--skills-count', '0',
        '--target-file-count', '2',
    )
    assert result.returncode == 0
    assert 'status: success' in result.stdout
    assert 'cost_size: S' in result.stdout


def test_cli_derive_cost_size_emits_predicted_tokens():
    """The subcommand emits predicted_cost_tokens for the derived size."""
    result = run_script(
        SCRIPT_PATH,
        'derive-cost-size',
        '--step-count', '14',
        '--profile', 'implementation',
        '--skills-count', '2',
        '--target-file-count', '6',
    )
    assert result.returncode == 0
    assert 'cost_size: L' in result.stdout
    assert 'predicted_cost_tokens: 130000' in result.stdout


def test_cli_derive_cost_size_honors_injected_size_table():
    """The --size-table flag injects a custom token magnitude."""
    result = run_script(
        SCRIPT_PATH,
        'derive-cost-size',
        '--step-count', '14',
        '--profile', 'implementation',
        '--skills-count', '2',
        '--target-file-count', '6',
        '--size-table', '{"S": "1K", "M": "2K", "L": "3K", "XL": "4K"}',
    )
    assert result.returncode == 0
    assert 'cost_size: L' in result.stdout
    assert 'predicted_cost_tokens: 3000' in result.stdout


def test_cli_derive_cost_size_rejects_malformed_size_table_json():
    """A malformed --size-table JSON yields a status: error TOON (exit 0)."""
    result = run_script(
        SCRIPT_PATH,
        'derive-cost-size',
        '--step-count', '3',
        '--profile', 'verification',
        '--skills-count', '0',
        '--target-file-count', '2',
        '--size-table', '{not valid json',
    )
    assert result.returncode == 0
    assert 'status: error' in result.stdout


def test_cli_derive_cost_size_rejects_negative_count():
    """A negative count yields a status: error TOON (deriver ValueError)."""
    result = run_script(
        SCRIPT_PATH,
        'derive-cost-size',
        '--step-count', '-1',
        '--profile', 'implementation',
        '--skills-count', '0',
        '--target-file-count', '0',
    )
    assert result.returncode == 0
    assert 'status: error' in result.stdout


def test_cli_derive_cost_size_missing_required_arg_exits_2():
    """Omitting a required signal flag is an argparse rejection (exit 2)."""
    result = run_script(
        SCRIPT_PATH,
        'derive-cost-size',
        '--profile', 'implementation',
        '--skills-count', '0',
        '--target-file-count', '0',
    )
    assert result.returncode == 2
