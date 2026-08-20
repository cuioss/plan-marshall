#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the deterministic envelope bin-packer (_tasks_envelope.py)."""


import json

from _tasks_envelope_fixtures import SCRIPT_PATH, _seed_task_file

from conftest import run_script

# =============================================================================
# pack-envelopes — CLI plumbing (Tier 3, on-disk task files)
# =============================================================================

def test_cli_pack_envelopes_returns_success(plan_context):
    """The pack-envelopes subcommand returns a success TOON with envelope_count."""
    plan_dir = plan_context.plan_dir_for('env-success')
    _seed_task_file(plan_dir, 1, 60)
    _seed_task_file(plan_dir, 2, 60)

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-success',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'status: success' in result.stdout
    assert 'envelope_count: 2' in result.stdout


def test_cli_pack_envelopes_single_envelope(plan_context):
    """Tasks that fit one envelope report envelope_count 1."""
    plan_dir = plan_context.plan_dir_for('env-single')
    _seed_task_file(plan_dir, 1, 30)
    _seed_task_file(plan_dir, 2, 30)

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-single',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'envelope_count: 1' in result.stdout


def test_cli_pack_envelopes_empty_plan(plan_context):
    """A plan with no tasks packs into zero envelopes."""
    plan_context.plan_dir_for('env-empty')

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-empty',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'status: success' in result.stdout
    assert 'envelope_count: 0' in result.stdout


def test_cli_pack_envelopes_rejects_non_positive_budget(plan_context):
    """A non-positive budget yields a status: error TOON (packer ValueError)."""
    plan_dir = plan_context.plan_dir_for('env-bad-budget')
    _seed_task_file(plan_dir, 1, 30)

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-bad-budget',
        '--per-envelope-budget-tokens', '0',
    )

    assert result.returncode == 0
    assert 'status: error' in result.stdout


def test_cli_pack_envelopes_reports_error_for_unsized_task(plan_context):
    """A task missing predicted_cost_tokens yields a status: error TOON."""
    plan_dir = plan_context.plan_dir_for('env-unsized')
    tasks_dir = plan_dir / 'tasks'
    tasks_dir.mkdir(parents=True, exist_ok=True)
    (tasks_dir / 'TASK-001.json').write_text(
        json.dumps({'number': 1, 'title': 'unsized', 'steps': []}, indent=2),
        encoding='utf-8',
    )

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-unsized',
        '--per-envelope-budget-tokens', '100',
    )

    assert result.returncode == 0
    assert 'status: error' in result.stdout


def test_cli_pack_envelopes_missing_budget_arg_exits_2(plan_context):
    """Omitting the required --per-envelope-budget-tokens flag is an argparse rejection."""
    plan_context.plan_dir_for('env-no-budget')

    result = run_script(
        SCRIPT_PATH,
        'pack-envelopes',
        '--plan-id', 'env-no-budget',
    )

    assert result.returncode == 2
