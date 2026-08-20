#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for deterministic task cost-sizing (_tasks_cost.py)."""


import pytest
from _tasks_cost_fixtures import (
    COST_SIZES,
    SCRIPT_PATH,
    _score_only,
    derive_cost_size,
    resolve_size_table,
    score_to_size,
)

from conftest import run_script

# =============================================================================
# resolve_size_table
# =============================================================================


def test_resolve_size_table_default_parses_magnitudes():
    """The default table parses every magnitude string to an int."""
    table = resolve_size_table(None)
    assert set(table) == set(COST_SIZES)
    assert all(isinstance(v, int) for v in table.values())


def test_resolve_size_table_default_matches_rubric_defaults():
    """The default resolved table matches the parsed DEFAULT_SIZE_TABLE.

    The four original magnitudes (S/M/L/XL) are UNCHANGED; XS and XXL are the
    two new ends.
    """
    table = resolve_size_table(None)
    assert table['XS'] == 5_000
    assert table['S'] == 25_000
    assert table['M'] == 60_000
    assert table['L'] == 130_000
    assert table['XL'] == 260_000
    assert table['XXL'] == 520_000


def test_resolve_size_table_default_is_monotone():
    """Larger sizes map to larger token magnitudes across the full six-size scale."""
    table = resolve_size_table(None)
    assert table['XS'] < table['S'] < table['M'] < table['L'] < table['XL'] < table['XXL']


def test_resolve_size_table_accepts_injected_table():
    """A caller-injected table overrides the default and is parsed."""
    injected = {'XS': '1K', 'S': '2K', 'M': '3K', 'L': '4K', 'XL': '5K', 'XXL': '6K'}
    table = resolve_size_table(injected)
    assert table == {'XS': 1000, 'S': 2000, 'M': 3000, 'L': 4000, 'XL': 5000, 'XXL': 6000}


def test_resolve_size_table_accepts_int_values():
    """A table with plain int values resolves unchanged."""
    injected = {'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6}
    table = resolve_size_table(injected)
    assert table == {'XS': 1, 'S': 2, 'M': 3, 'L': 4, 'XL': 5, 'XXL': 6}


def test_resolve_size_table_rejects_missing_key():
    """A table missing a required size key raises ValueError naming that key."""
    with pytest.raises(ValueError, match='XL'):
        resolve_size_table({'XS': '1K', 'S': '1K', 'M': '2K', 'L': '3K', 'XXL': '6K'})


def test_resolve_size_table_rejects_missing_new_xs_key():
    """A table missing the new XS key raises ValueError naming it."""
    with pytest.raises(ValueError, match='XS'):
        resolve_size_table({'S': '1K', 'M': '2K', 'L': '3K', 'XL': '4K', 'XXL': '6K'})


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
    injected = {'XS': '6K', 'S': '7K', 'M': '8K', 'L': '9K', 'XL': '10K', 'XXL': '11K'}
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
        (1, 'verification', 0, 1, 'XS'),      # 1-step doc-only verify -> score 18
        (5, 'verification', 1, 5, 'M'),       # 5-step documentation edit -> score 77
        (3, 'verification', 0, 2, 'S'),       # 3-step doc-only verify -> score 42
        (14, 'implementation', 2, 6, 'L'),    # 14-step config change -> score 182
        (55, 'module_testing', 3, 20, 'XL'),  # 55-step multi-file test refactor -> score 651
        (70, 'module_testing', 4, 25, 'XXL'), # 70-step multi-module test rewrite -> score 824
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
        '--size-table', '{"XS": "1K", "S": "1K", "M": "2K", "L": "3K", "XL": "4K", "XXL": "5K"}',
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
