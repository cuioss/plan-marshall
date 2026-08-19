#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``qgate-mechanical-checks`` subcommand of manage-tasks."""


from __future__ import annotations

import json

from _manage_tasks_qgate_mechanical_fixtures import (
    _EXISTING_FILE,
    _MISSING_FILE,
    _files_exist_failed,
    _ns,
    _qgate_mod,
    _seed_one_coverage_failure,
    _write_outline,
    _write_task,
    cmd_qgate_mechanical,
)

# =============================================================================
# Acyclic check
# =============================================================================


def test_qgate_mechanical_acyclic_simple_cycle(plan_context):
    """TASK-1 -> TASK-2 -> TASK-1 produces one finding."""
    plan_dir = plan_context.plan_dir_for('qgate-cycle')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        depends_on=['TASK-2'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )
    _write_task(
        plan_dir / 'tasks',
        2,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        depends_on=['TASK-1'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-cycle'))
    assert result['checks']['acyclic']['failed'] == 1


def test_qgate_mechanical_acyclic_dag_passes(plan_context):
    """A linear dependency chain is a DAG and passes."""
    plan_dir = plan_context.plan_dir_for('qgate-dag')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
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
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        depends_on=['TASK-1'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-dag'))
    assert result['checks']['acyclic']['failed'] == 0


# =============================================================================
# Files-exist check
# =============================================================================


def test_qgate_mechanical_files_exist_missing_step_target(plan_context):
    """A step target that doesn't exist on disk is flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-files-missing')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_MISSING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _MISSING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-files-missing'))
    assert result['checks']['files_exist']['failed'] == 1


def test_qgate_files_exist_read_missing_flags(plan_context):
    """read + missing target → 1 finding (current behaviour preserved)."""
    assert _files_exist_failed(plan_context, 'qgate-read-missing', _MISSING_FILE, 'read') == 1


def test_qgate_files_exist_read_present_passes(plan_context):
    """read + existing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-read-present', _EXISTING_FILE, 'read') == 0


def test_qgate_files_exist_write_new_missing_passes(plan_context):
    """write-new + missing target → 0 findings (the noise class this plan removes)."""
    assert _files_exist_failed(plan_context, 'qgate-writenew-missing', _MISSING_FILE, 'write-new') == 0


def test_qgate_files_exist_write_new_present_flags(plan_context):
    """write-new + existing target → 1 finding (inverted signal fires)."""
    assert _files_exist_failed(plan_context, 'qgate-writenew-present', _EXISTING_FILE, 'write-new') == 1


def test_qgate_files_exist_write_replace_missing_passes(plan_context):
    """write-replace + missing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-writerepl-missing', _MISSING_FILE, 'write-replace') == 0


def test_qgate_files_exist_write_replace_present_passes(plan_context):
    """write-replace + existing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-writerepl-present', _EXISTING_FILE, 'write-replace') == 0


def test_qgate_files_exist_delete_missing_flags(plan_context):
    """delete + missing target → 1 finding (delete-specific message)."""
    assert _files_exist_failed(plan_context, 'qgate-delete-missing', _MISSING_FILE, 'delete') == 1


def test_qgate_files_exist_delete_present_passes(plan_context):
    """delete + existing target → 0 findings."""
    assert _files_exist_failed(plan_context, 'qgate-delete-present', _EXISTING_FILE, 'delete') == 0


def test_qgate_mechanical_files_exist_skips_verification_profile(plan_context):
    """Verification profile steps are commands, not files, so are skipped."""
    plan_dir = plan_context.plan_dir_for('qgate-files-verify')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
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
        steps=[{'number': 1, 'target': 'pw verify --module plan-marshall', 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-files-verify'))
    assert result['checks']['files_exist']['failed'] == 0


# =============================================================================
# Keyword drift check
# =============================================================================


def test_qgate_mechanical_keyword_drift_planning_keyword_in_description(plan_context):
    """A planning-domain keyword absent from the deliverable haystack is flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-kw-drift')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'Implement foo', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        description="'Implement foo'. Update PR review workflow for CI compliance.",
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-kw-drift'))
    # "PR review" and "CI" both fire.
    assert result['checks']['keyword_drift']['failed'] >= 2


def test_qgate_mechanical_keyword_drift_keyword_in_haystack_is_ok(plan_context):
    """A planning keyword present in the deliverable haystack is not flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-kw-ok')
    _write_outline(
        plan_dir,
        [
            {
                'number': 1,
                'title': 'Wire CI pipeline',
                'affected_files': [_EXISTING_FILE],
                'metadata': {'change_type': 'feature'},
            }
        ],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        description="'Wire CI pipeline'. Update CI configuration to use the new runner.",
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-kw-ok'))
    assert result['checks']['keyword_drift']['failed'] == 0


# =============================================================================
# Structural-token drift (TASK-N numbering monotonic) check
# =============================================================================


def test_qgate_mechanical_structural_token_gap(plan_context):
    """A gap in TASK-NNN numbering is flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-numbering-gap')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )
    # Skip TASK-2 to leave a gap.
    _write_task(
        plan_dir / 'tasks',
        3,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-numbering-gap'))
    assert result['checks']['structural_token_drift']['failed'] >= 1


def test_qgate_mechanical_structural_token_does_not_start_at_001(plan_context):
    """Lowest task being ``TASK-002`` is flagged."""
    plan_dir = plan_context.plan_dir_for('qgate-numbering-start')
    _write_outline(
        plan_dir,
        [{'number': 1, 'title': 'X', 'affected_files': [_EXISTING_FILE]}],
    )
    _write_task(
        plan_dir / 'tasks',
        2,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-numbering-start'))
    # Both "doesn't start at 001" and the gap at ``TASK-001`` are reported.
    assert result['checks']['structural_token_drift']['failed'] >= 1


# =============================================================================
# Ambiguous flag + plan-dir handling
# =============================================================================


def test_qgate_mechanical_missing_outline_marks_ambiguous(plan_context):
    """When solution_outline.md is missing, ``ambiguous`` flips to True."""
    plan_dir = plan_context.plan_dir_for('qgate-no-outline')
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-no-outline'))
    assert result['ambiguous'] is True


def test_qgate_mechanical_plan_dir_not_found_errors(plan_context):
    """Missing plan dir returns a structured error."""
    # PlanContext creates the plan dir; query a different id that doesn't exist.
    result = cmd_qgate_mechanical(_ns('does-not-exist'))
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Emission path (writes findings to the Q-Gate JSONL store)
# =============================================================================


def test_qgate_mechanical_emit_writes_findings(plan_context):
    """With emit=True (default), failures land in the phase-4-plan Q-Gate findings store."""
    plan_dir = plan_context.plan_dir_for('qgate-emit')
    _write_outline(
        plan_dir,
        [
            {'number': 1, 'title': 'Has tasks', 'affected_files': [_EXISTING_FILE]},
            {'number': 2, 'title': 'No tasks', 'affected_files': ['src/B.java (read)']},
        ],
    )
    _write_task(
        plan_dir / 'tasks',
        1,
        deliverable=1,
        skills=['plan-marshall:manage-tasks'],
        steps=[{'number': 1, 'target': _EXISTING_FILE, 'status': 'pending'}],
    )

    result = cmd_qgate_mechanical(_ns('qgate-emit', no_emit=False))
    assert result['status'] == 'success'
    assert result['findings_emitted'] == 1
    assert result['emit'] is True
    # The Q-Gate JSONL store records the finding under phase 4-plan.
    findings_path = plan_dir / 'artifacts' / 'findings' / 'qgate-4-plan.jsonl'
    assert findings_path.exists(), 'qgate findings file was not created'
    records = [json.loads(line) for line in findings_path.read_text().splitlines() if line.strip()]
    assert len(records) == 1
    assert records[0]['source'] == 'qgate'
    assert records[0]['type'] == 'triage'
    assert 'coverage' in records[0]['title']
    # A clean emit run reports no persist failure.
    assert result['qgate_persist_failed'] is False
    assert result['qgate_persist_failures'] == []


def test_qgate_mechanical_rejected_persist_surfaces_failure(plan_context, monkeypatch):
    """A REJECTED persist surfaces qgate_persist_failed plus the primitive's message.

    Driven by the live failure mode — a finding type outside ``FINDING_TYPES``,
    which the real ``add_qgate_finding`` validator rejects — not a synthetic mock.
    """
    plan_dir = _seed_one_coverage_failure(plan_context, 'qgate-persist-reject')
    monkeypatch.setattr(_qgate_mod, '_FINDING_TYPE', 'not-a-finding-type')

    result = cmd_qgate_mechanical(_ns('qgate-persist-reject', no_emit=False))

    assert result['qgate_persist_failed'] is True
    assert len(result['qgate_persist_failures']) == 1
    failure = result['qgate_persist_failures'][0]
    assert 'coverage' in failure['title']
    assert 'Invalid finding type' in failure['message']
    # The rejection must NOT be reported as a benign no-op.
    assert result['findings_emitted'] == 0
    findings_path = plan_dir / 'artifacts' / 'findings' / 'qgate-4-plan.jsonl'
    assert not findings_path.exists(), 'a rejected persist must leave no stored record'


def test_qgate_mechanical_deduplicated_persist_stays_benign(plan_context):
    """A ``deduplicated`` outcome is benign — it must not collapse onto a rejection.

    The second emit run re-detects the same failure, so the primitive dedups it.
    The record is still in the store, so no persist failure is reported.
    """
    _seed_one_coverage_failure(plan_context, 'qgate-persist-dedup')

    first = cmd_qgate_mechanical(_ns('qgate-persist-dedup', no_emit=False))
    assert first['findings_emitted'] == 1
    assert first['qgate_persist_failed'] is False

    second = cmd_qgate_mechanical(_ns('qgate-persist-dedup', no_emit=False))

    assert second['qgate_persist_failed'] is False
    assert second['qgate_persist_failures'] == []
    # ``findings_emitted`` counts appends, and a dedup appends nothing — but that
    # zero means "already in the store", never "rejected".
    assert second['findings_emitted'] == 0
