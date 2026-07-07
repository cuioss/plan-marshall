#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the batched raw_input ingestion pass (_findings_ingest.py).

Covers batch promotion of quarantined ``raw_input.{field}`` values to top-level
fields, per-field ``maxLength`` clamp reporting via ``clamped``, validator
rejection routing to the ``rejected`` resolution, and the core containment
invariant: NO top-level field is ever populated from an un-validated ``raw_input``
value. Both the per-plan and per-phase Q-Gate slices are exercised, plus a CLI
plumbing roundtrip that proves the cross-skill ``validate_struct`` import chain
resolves at subprocess runtime.
"""

from conftest import get_script_path, load_script_module, run_script

# Script path for the CLI plumbing (subprocess) test.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-findings', 'manage-findings.py')

# Tier 2 direct imports — load the underscore-prefixed sibling modules. Loading
# _findings_core first registers it in sys.modules so _findings_ingest's
# `from _findings_core import ...` resolves to the same instance.
_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py')
_ingest = load_script_module('plan-marshall', 'manage-findings', '_findings_ingest.py')

add_finding = _core.add_finding
add_qgate_finding = _core.add_qgate_finding
query_findings = _core.query_findings
query_qgate_findings = _core.query_qgate_findings
ingest_findings = _ingest.ingest_findings


# =============================================================================
# Test: Batch promotion of raw_input to top-level
# =============================================================================


def test_ingest_promotes_raw_input_to_top_level(plan_context):
    """Validated raw_input.{field} values are promoted to the top-level fields."""
    pid = 'ingest-promote'
    add_finding(
        plan_id=pid,
        finding_type='pr-comment',
        title='t',
        detail='placeholder',
        raw_input={'detail': 'clean detail text', 'body': 'reviewer body'},
    )

    result = ingest_findings(pid)
    assert result['status'] == 'success'
    assert result['promoted'] == 1
    assert result['rejected'] == 0

    record = query_findings(pid)['findings'][0]
    # detail (placeholder) is overwritten by the validated raw_input value; body
    # (a new field) is added at the top level.
    assert record['detail'] == 'clean detail text'
    assert record['body'] == 'reviewer body'
    # The finding stays pending so the triage pass processes the promoted value.
    assert record['resolution'] == 'pending'


def test_ingest_leaves_raw_input_in_place_for_audit(plan_context):
    """Promotion copies to top-level but leaves the raw_input sub-object intact."""
    pid = 'ingest-audit'
    add_finding(
        plan_id=pid,
        finding_type='pr-comment',
        title='t',
        detail='ph',
        raw_input={'detail': 'clean', 'body': 'raw body'},
    )

    ingest_findings(pid)

    record = query_findings(pid)['findings'][0]
    assert record['raw_input']['detail'] == 'clean'
    assert record['raw_input']['body'] == 'raw body'


def test_ingest_promotes_all_declared_free_text_fields(plan_context):
    """title/detail/body/message/summary all promote when validly declared."""
    pid = 'ingest-all-fields'
    add_finding(
        plan_id=pid,
        finding_type='sonar-issue',
        title='ph-title',
        detail='ph-detail',
        raw_input={
            'title': 'clean title',
            'detail': 'clean detail',
            'body': 'clean body',
            'message': 'clean message',
            'summary': 'clean summary',
        },
    )

    result = ingest_findings(pid)
    assert result['promoted'] == 1

    record = query_findings(pid)['findings'][0]
    assert record['title'] == 'clean title'
    assert record['detail'] == 'clean detail'
    assert record['body'] == 'clean body'
    assert record['message'] == 'clean message'
    assert record['summary'] == 'clean summary'


# =============================================================================
# Test: Clamp reporting
# =============================================================================


def test_ingest_clamps_overlong_field_and_reports_clamped(plan_context):
    """A raw_input value over the schema maxLength is clamped and reported."""
    pid = 'ingest-clamp'
    long_detail = 'x' * 9000  # under the 64 KiB byte cap, over the 8000-char schema cap
    add_finding(plan_id=pid, finding_type='bug', title='t', detail='ph', raw_input={'detail': long_detail})

    result = ingest_findings(pid)
    assert result['promoted'] == 1
    assert any('detail' in report for report in result['clamped'])

    record = query_findings(pid)['findings'][0]
    assert len(record['detail']) == 8000
    assert record['detail'] == 'x' * 8000


# =============================================================================
# Test: Validator rejection routing
# =============================================================================


def test_ingest_rejects_undeclared_field_and_resolves_rejected(plan_context):
    """An undeclared raw_input field rejects the whole struct → finding rejected."""
    pid = 'ingest-reject'
    add_finding(plan_id=pid, finding_type='bug', title='t', detail='ph', raw_input={'notafield': 'x'})

    result = ingest_findings(pid)
    assert result['rejected'] == 1
    assert result['promoted'] == 0

    record = query_findings(pid)['findings'][0]
    assert record['resolution'] == 'rejected'
    # The undeclared field is never promoted to the top level.
    assert 'notafield' not in record
    # The resolution_detail names why ingestion rejected.
    assert record['resolution_detail']
    assert 'raw_input ingestion rejected' in record['resolution_detail']


def test_ingest_rejected_struct_promotes_nothing(plan_context):
    """A partially-valid struct with ONE bad field rejects entirely — the core
    containment invariant: no top-level field is populated from an un-validated
    raw_input, even the fields that would individually have validated.
    """
    pid = 'ingest-reject-invariant'
    add_finding(
        plan_id=pid,
        finding_type='bug',
        title='t',
        detail='placeholder',
        raw_input={'detail': 'would-be-valid', 'bad': 'y'},
    )

    ingest_findings(pid)

    record = query_findings(pid)['findings'][0]
    # additionalProperties:false rejects the whole struct → the valid `detail`
    # is NOT promoted; the top-level placeholder is left untouched.
    assert record['detail'] == 'placeholder'
    assert record['resolution'] == 'rejected'


# =============================================================================
# Test: Skip findings without raw_input
# =============================================================================


def test_ingest_skips_findings_without_raw_input(plan_context):
    """A finding with no raw_input is skipped — its clean top-level is untouched."""
    pid = 'ingest-skip'
    add_finding(plan_id=pid, finding_type='bug', title='t', detail='clean', raw_input=None)

    result = ingest_findings(pid)
    assert result['skipped'] == 1
    assert result['promoted'] == 0
    assert result['rejected'] == 0

    record = query_findings(pid)['findings'][0]
    assert record['detail'] == 'clean'
    assert record['resolution'] == 'pending'


# =============================================================================
# Test: Batch mixed outcomes
# =============================================================================


def test_ingest_batch_mixed_outcomes(plan_context):
    """One pass tallies promoted / rejected / skipped across a mixed batch."""
    pid = 'ingest-mixed'
    add_finding(plan_id=pid, finding_type='bug', title='a', detail='ph', raw_input={'detail': 'ok'})
    add_finding(plan_id=pid, finding_type='bug', title='b', detail='ph', raw_input={'bad': 'x'})
    add_finding(plan_id=pid, finding_type='bug', title='c', detail='clean')

    result = ingest_findings(pid)
    assert result['promoted'] == 1
    assert result['rejected'] == 1
    assert result['skipped'] == 1
    assert len(result['outcomes']) == 3


def test_ingest_empty_plan_returns_zero_counts(plan_context):
    """Ingesting an empty plan returns the success shape with zero counts."""
    result = ingest_findings('ingest-empty')
    assert result['status'] == 'success'
    assert result['promoted'] == 0
    assert result['rejected'] == 0
    assert result['skipped'] == 0
    assert result['outcomes'] == []


def test_ingest_is_idempotent_on_promoted_findings(plan_context):
    """Re-running ingest re-promotes the same clean value — no drift, no rejection."""
    pid = 'ingest-idem'
    add_finding(plan_id=pid, finding_type='bug', title='t', detail='ph', raw_input={'detail': 'clean'})

    ingest_findings(pid)
    second = ingest_findings(pid)

    assert second['promoted'] == 1
    assert second['rejected'] == 0
    record = query_findings(pid)['findings'][0]
    assert record['detail'] == 'clean'


# =============================================================================
# Test: Q-Gate slice
# =============================================================================


def test_ingest_qgate_finding_promoted(plan_context):
    """The ingestion pass promotes pending Q-Gate findings' raw_input too."""
    pid = 'ingest-qgate'
    add_qgate_finding(
        plan_id=pid,
        phase='5-execute',
        source='qgate',
        finding_type='triage',
        title='t',
        detail='ph',
        raw_input={'detail': 'clean qgate detail'},
    )

    result = ingest_findings(pid)
    assert result['promoted'] == 1

    record = query_qgate_findings(pid, '5-execute')['findings'][0]
    assert record['detail'] == 'clean qgate detail'
    assert record['raw_input']['detail'] == 'clean qgate detail'


def test_ingest_qgate_rejected_excluded_from_pending(plan_context):
    """A rejected Q-Gate finding closes non-pending and drops out of the pending read."""
    pid = 'ingest-qgate-reject'
    add_qgate_finding(
        plan_id=pid,
        phase='5-execute',
        source='qgate',
        finding_type='triage',
        title='t',
        detail='ph',
        raw_input={'bad': 'x'},
    )

    result = ingest_findings(pid)
    assert result['rejected'] == 1

    pending = query_qgate_findings(pid, '5-execute', resolution='pending')
    assert pending['filtered_count'] == 0
    rejected = query_qgate_findings(pid, '5-execute', resolution='rejected')
    assert rejected['filtered_count'] == 1


# =============================================================================
# Test: CLI plumbing (subprocess) — proves the cross-skill import chain resolves
# =============================================================================


def test_cli_ingest_roundtrip(plan_context):
    """CLI plumbing: `add --raw-input` then `ingest` promotes via subprocess.

    Exercising the verb through a real subprocess proves the
    manage-findings → _findings_ingest → validate_struct cross-skill import
    chain resolves under the executor-mirrored PYTHONPATH.
    """
    pid = 'cli-ingest-rt'
    add_result = run_script(
        SCRIPT_PATH,
        'add',
        '--plan-id',
        pid,
        '--type',
        'pr-comment',
        '--title',
        't',
        '--detail',
        'ph',
        '--raw-input',
        'detail=clean via cli',
    )
    assert add_result.success, f'add failed: {add_result.stderr}'

    ingest_result = run_script(SCRIPT_PATH, 'ingest', '--plan-id', pid)
    assert ingest_result.success, f'ingest failed: {ingest_result.stderr}'
    data = ingest_result.toon()
    assert data['status'] == 'success'
    assert data['promoted'] == 1
