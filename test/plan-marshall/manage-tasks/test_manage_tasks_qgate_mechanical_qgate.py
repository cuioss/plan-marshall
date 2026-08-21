#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``qgate-mechanical-checks`` subcommand of manage-tasks.

Its sections, in order:

* Smoke / happy-path
* Coverage check
* Skill resolution check
"""


from __future__ import annotations

from _manage_tasks_qgate_mechanical_fixtures import (
    _ALL_CHECKS,
    _EXISTING_FILE,
    _ns,
    _write_outline,
    _write_task,
    cmd_qgate_mechanical,
)

# =============================================================================
# Smoke / happy-path
# =============================================================================


def test_qgate_mechanical_clean_plan_passes_all_checks(plan_context):
    """A consistent plan with two deliverables × one task each reports zero failures."""
    plan_dir = plan_context.plan_dir_for('qgate-clean')
    _write_outline(
        plan_dir,
        [
            {'number': 1, 'title': 'Add foo', 'affected_files': [_EXISTING_FILE]},
            {'number': 2, 'title': 'Add bar', 'affected_files': [_EXISTING_FILE]},
        ],
    )
    # Both deliverables declare the file their task targets, so the declared set
    # is closed as well as resolvable — files_exist AND the closure checks pass.
    task_dir = plan_dir / 'tasks'
    _write_task(
        task_dir,
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )
    _write_task(
        task_dir,
        2,
        deliverable=2,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-clean'))

    assert result['status'] == 'success'
    assert result['total_failed'] == 0
    assert result['findings_emitted'] == 0  # --no-emit path
    assert result['ambiguous'] is False
    assert set(result['checks']) == set(_ALL_CHECKS), 'the asserted name set must be the live one'
    for name in _ALL_CHECKS:
        assert result['checks'][name]['failed'] == 0, name


# =============================================================================
# Coverage check
# =============================================================================


def test_qgate_mechanical_coverage_missing_deliverable(plan_context):
    """A deliverable with no tasks is flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-cov-missing')
    _write_outline(
        plan_dir,
        [
            {'number': 1, 'title': 'Add foo', 'affected_files': [_EXISTING_FILE]},
            {'number': 2, 'title': 'Add bar', 'affected_files': ['src/B.java (read)']},
        ],
    )
    # Only deliverable 1 has a task; deliverable 2 is uncovered.
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-cov-missing'))
    assert result['checks']['coverage']['failed'] == 1


def test_qgate_mechanical_coverage_orphan_task(plan_context):
    """A task referencing a non-existent deliverable is flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-cov-orphan')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'Add foo', 'affected_files': [_EXISTING_FILE]}],
    )
    # deliverable=2 references unknown deliverable -> orphan.
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )
    _write_task(
        plan_dir / 'tasks',
        2,
        deliverable=42,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-cov-orphan'))
    # One orphan task; deliverable 1 is covered.
    assert result['checks']['coverage']['failed'] == 1


def test_qgate_mechanical_holistic_task_not_orphan(plan_context):
    """deliverable=0 (holistic) does not count as an orphan."""
    plan_dir = plan_context.plan_dir_for('qgate-cov-holistic')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'Add foo', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )
    _write_task(
        plan_dir / 'tasks',
        2,
        deliverable=0,
        profile='verification',
        domain='',
        skills=[],
        steps=[{'number': 1, 'target': 'pw verify', 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-cov-holistic'))
    assert result['checks']['coverage']['failed'] == 0


# =============================================================================
# Skill resolution check
# =============================================================================


def test_qgate_mechanical_skill_resolution_missing_domain(plan_context):
    """Non-verification tasks without a domain are flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-skill-nodomain')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        domain='',  # missing
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-skill-nodomain'))
    assert result['checks']['skill_resolution']['failed'] >= 1


def test_qgate_mechanical_skill_resolution_bad_shape(plan_context):
    """Skill strings not matching ``bundle:skill`` shape are flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-skill-shape')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['no-colon-here', 'plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-skill-shape'))
    # Exactly one bad skill.
    assert result['checks']['skill_resolution']['failed'] == 1


def test_qgate_mechanical_skill_resolution_empty_skills_allowed(plan_context):
    """Empty skills list is permitted (Step 5 records its own finding)."""
    plan_dir = plan_context.plan_dir_for('qgate-skill-empty')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=[],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-skill-empty'))
    assert result['checks']['skill_resolution']['failed'] == 0
