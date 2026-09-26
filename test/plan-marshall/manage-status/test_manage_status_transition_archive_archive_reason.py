# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_manage_status_transition_archive_fixtures import (
    SCRIPT_PATH,
    Namespace,
    Path,
    _seed_finalize_phase_plan,
    _stub_finding_queries,
    cmd_archive,
    json,
    run_script,
)

# =============================================================================
# Test: cmd_archive --reason flag persistence
# =============================================================================


def test_archive_with_reason_persists_archived_reason_metadata(plan_context):
    """cmd_archive --reason=<value> must persist status.metadata.archived_reason."""
    plan_id = 'archive-reason-persists'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence'))

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status_path = Path(result['archived_to']) / 'status.json'
    assert archived_status_path.exists(), f'archived status.json missing at {archived_status_path}'

    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    assert 'metadata' in archived_status, (
        'archived status.json missing metadata block — cmd_archive failed '
        'to setdefault metadata before writing archived_reason'
    )
    assert archived_status['metadata'].get('archived_reason') == 'low_confidence', (
        f"Expected metadata.archived_reason='low_confidence', got "
        f'{archived_status["metadata"].get("archived_reason")!r}. '
        f'--reason flag did not persist via setdefault before write_status.'
    )


def test_archive_without_reason_omits_archived_reason_field(plan_context):
    """cmd_archive without --reason must NOT introduce an archived_reason field."""
    plan_id = 'archive-reason-omitted'
    _seed_finalize_phase_plan(plan_id)
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=None))

    assert result['status'] == 'success', f'archive failed: {result}'
    archived_status_path = Path(result['archived_to']) / 'status.json'
    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))

    metadata = archived_status.get('metadata', {})
    assert 'archived_reason' not in metadata, (
        f'Expected archived_reason absent from metadata when --reason '
        f'omitted, got metadata={metadata!r}. Additive-metadata contract '
        f'violated — cmd_archive must guard the write with '
        f'`if reason is not None:`.'
    )


def test_archive_reason_attribute_missing_does_not_raise(plan_context):
    """cmd_archive must tolerate Namespace without a ``reason`` attribute."""
    plan_id = 'archive-reason-attr-missing'
    _seed_finalize_phase_plan(plan_id)
    # Intentionally omit ``reason`` from Namespace to simulate legacy callers.
    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False))

    assert result['status'] == 'success', f'archive raised or failed when Namespace lacked reason attr: {result}'
    archived_status_path = Path(result['archived_to']) / 'status.json'
    archived_status = json.loads(archived_status_path.read_text(encoding='utf-8'))
    metadata = archived_status.get('metadata', {})
    assert 'archived_reason' not in metadata, f'Legacy Namespace path leaked an archived_reason key: {metadata!r}'


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
        f'CLI archive --reason failed (rc={result.returncode}): stdout={result.stdout!r} stderr={result.stderr!r}'
    )

    # Locate the archive by parsing the TOON output for ``archived_to``.
    archived_to_line = next(
        (line for line in result.stdout.splitlines() if 'archived_to' in line),
        None,
    )
    assert archived_to_line is not None, f'CLI output missing archived_to: {result.stdout!r}'
    archived_path = Path(archived_to_line.split(':', 1)[1].strip().strip('"'))
    archived_status = json.loads((archived_path / 'status.json').read_text(encoding='utf-8'))
    assert archived_status.get('metadata', {}).get('archived_reason') == 'orphan_directory', (
        f'CLI --reason did not round-trip into archived status.json: {archived_status.get("metadata")!r}'
    )


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
        'A --reason archive is a deliberate abandonment and must not be blocked by pending findings.'
    )
    assert 'archived_to' in result
