# SPDX-License-Identifier: FSL-1.1-ALv2

import _invariants as _inv
import pytest
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
from _manage_status_transition_fixtures import _lifecycle


@pytest.fixture
def _captured_log_entries(monkeypatch):
    """Capture ``_cmd_lifecycle``'s log_entry calls as ``(kind, plan_id, level, message)``.

    Patched on the lifecycle module object whose ``cmd_archive`` the fixtures
    export, which resolves ``log_entry`` as a module global.
    """
    entries: list[tuple] = []
    monkeypatch.setattr(_lifecycle, 'log_entry', lambda *args: entries.append(args))
    return entries


def _exemption_warnings(entries: list[tuple]) -> list[tuple]:
    """The WARNING decision entries a reason-exempted archive emits."""
    return [
        e
        for e in entries
        if e[0] == 'decision' and e[2] == 'WARNING' and 'exempted from the blocking-findings gate' in e[3]
    ]


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


def test_archive_with_reason_bypasses_findings_gate(plan_context, monkeypatch, _captured_log_entries):
    """A DELIBERATE archive (a non-completion --reason, e.g. abandonment) is exempt
    from the completion gate: it archives even with a pending actionable finding, so
    a low-confidence / abandoned plan is never stranded behind its own findings.
    The exemption covers the refusal, not the evaluation: the result reports the
    pending count and exactly one WARNING decision-log line names reason and count."""
    _stub_finding_queries(monkeypatch, {'build-error': 3})
    plan_id = 'finalize-abandon-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence'))

    assert result['status'] == 'success', (
        'A --reason archive is a deliberate abandonment and must not be blocked by pending findings.'
    )
    assert 'archived_to' in result
    assert result['findings_gate'] == 'exempted_by_reason'
    assert result['pending_actionable_count'] == 3

    warnings = _exemption_warnings(_captured_log_entries)
    assert len(warnings) == 1, f'expected exactly one exemption WARNING, got: {_captured_log_entries!r}'
    assert warnings[0][1] == plan_id
    assert 'low_confidence' in warnings[0][3]
    assert 'pending_actionable_count=3' in warnings[0][3]


def test_archive_with_normal_completion_reason_takes_the_gated_path(plan_context, monkeypatch):
    """A reason that ASSERTS completion is gated exactly like an absent reason: a
    plan open in 6-finalize with a pending actionable finding is REFUSED and its
    directory is not moved. Naming the completion can never disarm the gate that
    guards it."""
    _stub_finding_queries(monkeypatch, {'sonar-issue': 1})
    plan_id = 'finalize-normal-completion-archive'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='normal_completion'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert result['blocking_count'] == 1
    assert 'archived_to' not in result
    assert 'findings_gate' not in result
    assert (plan_context.plans_dir / plan_id / 'status.json').exists()


@pytest.mark.parametrize('reason', ['', '   ', '\t\n'], ids=['empty', 'spaces', 'tab-newline'])
def test_archive_refuses_an_empty_or_whitespace_reason(plan_context, monkeypatch, reason):
    """An empty or whitespace-only --reason names no reason, so it is refused with
    ``invalid_archive_reason`` and nothing is moved — it never reaches the exempt path."""
    _stub_finding_queries(monkeypatch, {'build-error': 1})
    plan_id = 'archive-empty-reason'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=reason))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_archive_reason'
    assert 'archived_to' not in result
    assert 'findings_gate' not in result
    assert (plan_context.plans_dir / plan_id / 'status.json').exists()


@pytest.mark.parametrize(
    'reason',
    [' normal_completion', 'normal_completion ', 'Normal_Completion', 'NORMAL_COMPLETION'],
    ids=['leading-space', 'trailing-space', 'title-case', 'upper-case'],
)
def test_archive_gates_spelling_variants_of_normal_completion(plan_context, monkeypatch, reason):
    """A completion-asserting reason is matched stripped and case-insensitively, so a
    spelling variant takes the gated path and is refused on a pending finding."""
    _stub_finding_queries(monkeypatch, {'sonar-issue': 1})
    plan_id = 'archive-normal-completion-variant'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason=reason))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'blocking_findings_present'
    assert 'findings_gate' not in result
    assert (plan_context.plans_dir / plan_id / 'status.json').exists()


def test_archive_persists_the_stripped_reason(plan_context, monkeypatch):
    """An accepted reason is persisted with surrounding whitespace removed."""
    _stub_finding_queries(monkeypatch, {})
    plan_id = 'archive-reason-stripped'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='  low_confidence \n'))

    assert result['status'] == 'success'
    assert result['findings_gate'] == 'exempted_by_reason'
    archived_status = json.loads((Path(result['archived_to']) / 'status.json').read_text(encoding='utf-8'))
    assert archived_status['metadata']['archived_reason'] == 'low_confidence'


def test_archive_cli_refuses_an_empty_reason(plan_context):
    """The CLI surface refuses ``--reason ''`` with the structured error and exit 0."""
    plan_id = 'archive-empty-reason-cli'
    _seed_finalize_phase_plan(plan_id)

    result = run_script(SCRIPT_PATH, 'archive', '--plan-id', plan_id, '--reason', '')

    assert result.returncode == 0, f'stdout={result.stdout!r} stderr={result.stderr!r}'
    assert 'invalid_archive_reason' in result.stdout
    assert (plan_context.plans_dir / plan_id / 'status.json').exists()


def test_exempt_archive_over_a_clean_store_still_reports_zero(plan_context, monkeypatch, _captured_log_entries):
    """An exempt archive is never silent: over a CLEAN store it still reports a
    measured ``0`` and still writes exactly one WARNING line carrying that count."""
    _stub_finding_queries(monkeypatch, {})
    plan_id = 'finalize-abandon-archive-clean'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence'))

    assert result['status'] == 'success'
    assert result['findings_gate'] == 'exempted_by_reason'
    assert result['pending_actionable_count'] == 0

    warnings = _exemption_warnings(_captured_log_entries)
    assert len(warnings) == 1, f'expected exactly one exemption WARNING, got: {_captured_log_entries!r}'
    assert 'low_confidence' in warnings[0][3]
    assert 'pending_actionable_count=0' in warnings[0][3]


def test_exempt_archive_reports_an_unevaluable_count_as_unevaluable(plan_context, monkeypatch, _captured_log_entries):
    """When the pending query cannot be evaluated, the count is the explicit
    ``unevaluable`` marker — never a ``0`` that would read as a clean store — and
    the single WARNING line carries the same marker."""
    monkeypatch.setattr(_inv, '_query_pending_count_for_type', lambda _pid, _ft: None)
    monkeypatch.setattr(_inv, '_query_pending_qgate_count_aggregated', lambda _pid: None)
    plan_id = 'finalize-abandon-archive-unevaluable'
    _seed_finalize_phase_plan(plan_id)

    result = cmd_archive(Namespace(plan_id=plan_id, dry_run=False, reason='low_confidence'))

    assert result['status'] == 'success'
    assert result['findings_gate'] == 'exempted_by_reason'
    assert result['pending_actionable_count'] == 'unevaluable'

    warnings = _exemption_warnings(_captured_log_entries)
    assert len(warnings) == 1, f'expected exactly one exemption WARNING, got: {_captured_log_entries!r}'
    assert 'pending_actionable_count=unevaluable' in warnings[0][3]


def test_archive_help_no_longer_offers_normal_completion(plan_context):
    """``archive --help`` must not offer ``normal_completion`` as an example reason:
    following the help used to disarm the gate on exactly the completion it guards."""
    result = run_script(SCRIPT_PATH, 'archive', '--help')

    assert result.returncode == 0, f'archive --help failed: {result.stderr!r}'
    assert '--reason' in result.stdout
    assert 'normal_completion' not in result.stdout
