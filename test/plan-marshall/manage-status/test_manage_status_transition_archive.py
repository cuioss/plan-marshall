#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for manage-status.py transition + archive + delete + orphans + loop-back."""


import json
from argparse import Namespace
from pathlib import Path

from _manage_status_transition_fixtures import (
    SCRIPT_PATH,
    _seed_finalize_phase_plan,
    _stub_finding_queries,
    cmd_archive,
    cmd_transition,
)

from conftest import run_script


def test_archive_marks_final_phase_done_and_sets_complete(plan_context):
    """cmd_archive must close the active phase + set current_phase=complete BEFORE the move."""
    plan_id = 'archive-atomic-happy-path'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive failed: {result}'
    assert 'archived_to' in result, f'missing archived_to in {result}'

    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), (
        f'archived status.json missing at {archived_status_path} — '
        f'either move failed or archived_to points to wrong path'
    )

    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    assert archived_status['current_phase'] == 'complete', (
        f"Expected archived current_phase='complete', got "
        f"{archived_status['current_phase']!r}. Atomic-archive fix "
        f'regressed: cmd_archive is not setting the post-finalize sentinel '
        f'before shutil.move runs.'
    )
    assert archived_status['phases'][-1]['status'] == 'done', (
        f"Expected archived phases[-1].status='done', got "
        f"{archived_status['phases'][-1]['status']!r}. Atomic-archive fix "
        f'regressed: cmd_archive is not marking the active phase done '
        f'before shutil.move runs.'
    )


def test_archive_dry_run_leaves_status_unchanged(plan_context):
    """--dry-run must NOT mutate status.json or create the archive directory."""
    plan_id = 'archive-atomic-dry-run'
    _seed_finalize_phase_plan(plan_id)

    live_status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    before = live_status_path.read_text(encoding='utf-8')

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True))

    assert result['status'] == 'success'
    assert result.get('dry_run') is True, f'missing dry_run flag: {result}'
    assert 'would_archive_to' in result
    assert 'archived_to' not in result, (
        f'dry-run must NOT report archived_to: {result}'
    )

    assert not Path(result['would_archive_to']).exists(), (
        f"dry-run created the archive dir at {result['would_archive_to']} — "
        f'atomic-archive write block leaked into the dry-run path; the '
        f'`if args.dry_run:` early-return must precede the write block.'
    )

    after = live_status_path.read_text(encoding='utf-8')
    assert before == after, (
        'dry-run mutated the live status.json — atomic-archive write '
        'block leaked into the dry-run path; verify the early-return '
        'on args.dry_run runs before the write_status call.'
    )


# =============================================================================
# Test: cmd_archive --reason flag persistence
# =============================================================================


def test_archive_with_reason_persists_archived_reason_metadata(plan_context):
    """cmd_archive --reason=<value> must persist status.metadata.archived_reason."""
    plan_id = 'archive-reason-persists'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(
        Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence')
    )

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), (
        f'archived status.json missing at {archived_status_path}'
    )

    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    assert 'metadata' in archived_status, (
        'archived status.json missing metadata block — cmd_archive failed '
        'to setdefault metadata before writing archived_reason'
    )
    assert archived_status['metadata'].get('archived_reason') == 'low_confidence', (
        f"Expected metadata.archived_reason='low_confidence', got "
        f"{archived_status['metadata'].get('archived_reason')!r}. "
        f'--reason flag did not persist via setdefault before write_status.'
    )


def test_archive_without_reason_omits_archived_reason_field(plan_context):
    """cmd_archive without --reason must NOT introduce an archived_reason field."""
    plan_id = 'archive-reason-omitted'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(
        Namespace(plan_id=plan_id, dry_run=False, reason=None)
    )

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status_path = Path(result['archived_to']) / 'status.json'
    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))

    metadata = archived_status.get('metadata', {})
    assert 'archived_reason' not in metadata, (
        f"Expected archived_reason absent from metadata when --reason "
        f"omitted, got metadata={metadata!r}. Additive-metadata contract "
        f"violated — cmd_archive must guard the write with "
        f"`if reason is not None:`."
    )


def test_archive_reason_attribute_missing_does_not_raise(plan_context):
    """cmd_archive must tolerate Namespace without a ``reason`` attribute."""
    plan_id = 'archive-reason-attr-missing'
    _seed_finalize_phase_plan(plan_id)
    # Intentionally omit ``reason`` from Namespace to simulate legacy callers.
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', (
        f'archive raised or failed when Namespace lacked reason attr: {result}'
    )
    archived_status_path = Path(result['archived_to']) / 'status.json'
    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    metadata = archived_status.get('metadata', {})
    assert 'archived_reason' not in metadata, (
        f'Legacy Namespace path leaked an archived_reason key: {metadata!r}'
    )


def test_archive_dry_run_with_reason_does_not_mutate_status(plan_context):
    """--dry-run with --reason must NOT mutate live status.json or archive."""
    plan_id = 'archive-reason-dry-run'
    _seed_finalize_phase_plan(plan_id)

    live_status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    before = live_status_path.read_text(encoding='utf-8')

    result = cmd_archive(
        Namespace(plan_id=plan_id, dry_run=True, reason='dangling_worktree')
    )

    assert result['status'] == 'success'
    assert result.get('dry_run') is True, f'missing dry_run flag: {result}'
    assert 'archived_to' not in result, (
        f'dry-run must NOT report archived_to even with --reason: {result}'
    )

    after = live_status_path.read_text(encoding='utf-8')
    assert before == after, (
        'dry-run with --reason mutated live status.json — the metadata '
        'write block leaked past the dry-run early-return.'
    )


def test_archive_reason_cli_round_trip_persists_to_archive(plan_context):
    """End-to-end CLI invocation: ``manage-status archive --reason=X`` persists."""
    plan_id = 'archive-reason-cli'
    _seed_finalize_phase_plan(plan_id)

    result = run_script(
        SCRIPT_PATH,
        'archive',
        '--plan-id',
        plan_id,
        '--reason',
        'orphan_directory',
    )
    assert result.returncode == 0, (
        f'CLI archive --reason failed (rc={result.returncode}): '
        f'stdout={result.stdout!r} stderr={result.stderr!r}'
    )

    # Locate the archive by parsing the TOON output for ``archived_to``.
    archived_to_line = next(
        (line for line in result.stdout.splitlines() if 'archived_to' in line),
        None,
    )
    assert archived_to_line is not None, (
        f'CLI output missing archived_to: {result.stdout!r}'
    )
    archived_path = Path(archived_to_line.split(':', 1)[1].strip().strip('"'))
    archived_status = json.loads(
        (archived_path / 'status.json').read_text(encoding='utf-8')
    )
    assert (
        archived_status.get('metadata', {}).get('archived_reason')
        == 'orphan_directory'
    ), (
        f'CLI --reason did not round-trip into archived status.json: '
        f'{archived_status.get("metadata")!r}'
    )


# =============================================================================
# D2 — Finalize completion boundary asserts the blocking-findings STATE.
#
# The blocking-findings gate historically fired only when a
# `phase_handshake capture --phase 6-finalize` CALL was issued during finalize;
# a missing call left no row and raised nothing, so a plan could complete with
# actionable findings still `pending`, and "the gate never ran" was
# indistinguishable from "the gate passed". cmd_transition (completing
# 6-finalize) and cmd_archive (normal completion) now assert the STATE directly,
# armed by REACHING the completion boundary rather than by an optional call.
#
# These controls are the deliverable's proof. The NEGATIVE controls drive a
# pending actionable finding through the REAL blocking-count predicate (via
# `_stub_finding_queries`, the same seam the 5->6 boundary tests use) and assert
# the completion is REFUSED — and refused ONLY because the gate was added, so
# each fails against the pre-fix code. The POSITIVE controls confirm a clean plan
# is still admitted, and the abandonment exemption confirms the gate discriminates
# on the completion intent rather than blocking unconditionally.
# =============================================================================

def test_archive_refuses_when_actionable_finding_pending(plan_context, monkeypatch):
    """NEGATIVE control: a normal-completion archive (no --reason) is REFUSED
    while an actionable finding is pending, and the plan dir is NOT moved."""
    _stub_finding_queries(monkeypatch, {'sonar-issue': 2})
    plan_id = 'finalize-block-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 2
    assert result['per_type']['sonar-issue'] == 2
    # The plan directory survives — no move happened.
    assert plan_context.plan_dir_for(plan_id).exists()
    assert 'archived_to' not in result


def test_archive_admits_when_no_actionable_finding(plan_context, monkeypatch):
    """POSITIVE control: a clean normal-completion archive proceeds."""
    _stub_finding_queries(monkeypatch, {})
    plan_id = 'finalize-clean-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result['status'] == 'success'
    assert 'archived_to' in result


def test_archive_with_reason_bypasses_findings_gate(plan_context, monkeypatch):
    """A DELIBERATE archive (--reason present, e.g. abandonment) is exempt from
    the completion gate: it archives even with a pending actionable finding, so a
    low-confidence / abandoned plan is never stranded behind its own findings.
    Confirms the gate discriminates on the completion intent."""
    _stub_finding_queries(monkeypatch, {'build-error': 3})
    plan_id = 'finalize-abandon-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence'))

    assert result['status'] == 'success', (
        'A --reason archive is a deliberate abandonment and must not be blocked '
        'by pending findings.'
    )
    assert 'archived_to' in result


def test_archive_dry_run_does_not_fire_findings_gate(plan_context, monkeypatch):
    """A dry-run archive returns before the gate — it makes no state change, so a
    pending finding must not turn a preview into a refusal."""
    _stub_finding_queries(monkeypatch, {'build-error': 1})
    plan_id = 'finalize-dryrun-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=True, reason=None))

    assert result['status'] == 'success'
    assert result.get('dry_run') is True
    assert 'would_archive_to' in result


def test_archive_of_already_complete_plan_not_blocked_by_pending_finding(plan_context, monkeypatch):
    """The cleanup pass archives already-`complete` plans (no --reason). A stale
    pending record on such a plan must NOT wedge cleanup — the completion gate
    fires only while the plan is actively in 6-finalize, not after it completed.
    This is exactly the pre-D3 residue (a permanently-pending qgate record) whose
    cleanup a broad gate would have blocked."""
    _stub_finding_queries(monkeypatch, {})  # clean, so the plan can complete
    plan_id = 'finalize-cleanup-complete'
    _seed_finalize_phase_plan(plan_id)
    # Complete it normally (clean) → current_phase becomes 'complete'.
    done = cmd_transition(Namespace(plan_id=plan_id, completed='6-finalize'))
    assert done['status'] == 'success'

    # A stale pending actionable record now appears (the pre-D3 residue).
    _stub_finding_queries(monkeypatch, {'build-error': 1})

    # The cleanup archive (no --reason) of the already-complete plan must proceed.
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))
    assert result['status'] == 'success', (
        'A cleanup archive of an already-complete plan must not be blocked by a '
        'stale pending finding — the completion gate fires only while in 6-finalize.'
    )
    assert 'archived_to' in result
