# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_record_step.py: record."""

from _manage_execution_manifest_record_step_fixtures import (
    EXECUTION_LOG_KEY,
    _compose,
    _record_ns,
    cmd_record_step,
    read_manifest,
)

# =============================================================================
# Append + token-attribution tests
# =============================================================================


def test_record_executed_appends_row_with_token_attribution(plan_context):
    """An executed record appends one row carrying its token-attribution triple."""
    _compose('rec-exec')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-exec',
            step_id='verify:quality-gate',
            phase='5-execute',
            outcome='executed',
            total_tokens=1200,
            tool_uses=7,
            duration_ms=4200,
        )
    )

    assert result is not None
    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['step_id'] == 'verify:quality-gate'
    assert result['phase'] == '5-execute'
    assert result['outcome'] == 'executed'
    assert result['total_tokens'] == 1200
    assert result['tool_uses'] == 7
    assert result['duration_ms'] == 4200
    assert result['execution_log_count'] == 1
    assert 'timestamp' in result


def test_record_executed_persists_row_to_manifest(plan_context):
    """The appended row is persisted into the manifest's execution_log section."""
    _compose('rec-persist')

    cmd_record_step(
        _record_ns(
            plan_id='rec-persist',
            step_id='verify:module-tests',
            total_tokens=900,
            tool_uses=3,
            duration_ms=1500,
        )
    )

    manifest = read_manifest('rec-persist')
    assert manifest is not None
    log = manifest[EXECUTION_LOG_KEY]
    assert isinstance(log, list)
    assert len(log) == 1
    entry = log[0]
    assert entry['step_id'] == 'verify:module-tests'
    assert entry['outcome'] == 'executed'
    assert entry['total_tokens'] == 900
    assert entry['tool_uses'] == 3
    assert entry['duration_ms'] == 1500
    assert 'timestamp' in entry


def test_record_skipped_appends_row(plan_context):
    """A skipped step records a row with the skipped outcome."""
    _compose('rec-skip')

    result = cmd_record_step(_record_ns(plan_id='rec-skip', step_id='verify:coverage', outcome='skipped'))

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'skipped'
    manifest = read_manifest('rec-skip')
    assert manifest is not None
    assert manifest[EXECUTION_LOG_KEY][0]['outcome'] == 'skipped'


def test_record_error_outcome_appends_row(plan_context):
    """An error step records a row with the error outcome."""
    _compose('rec-error')

    result = cmd_record_step(_record_ns(plan_id='rec-error', step_id='ci-verify', phase='6-finalize', outcome='error'))

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'error'
    assert result['phase'] == '6-finalize'


def test_record_negative_token_values_clamped_to_zero(plan_context):
    """Negative attribution inputs are clamped to zero (max(0, ...))."""
    _compose('rec-neg')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-neg',
            step_id='verify:quality-gate',
            total_tokens=-50,
            tool_uses=-1,
            duration_ms=-999,
        )
    )

    assert result is not None
    assert result['total_tokens'] == 0
    assert result['tool_uses'] == 0
    assert result['duration_ms'] == 0


# =============================================================================
# Ordered append-log semantics
# =============================================================================


def test_record_appends_in_order_and_count_increments(plan_context):
    """Repeated records append rows deterministically; reading back reflects order."""
    _compose('rec-order')

    r1 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='verify:quality-gate', outcome='executed'))
    r2 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='verify:module-tests', outcome='executed'))
    r3 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='verify:coverage', outcome='skipped'))

    # running count tracks the append log
    assert r1['execution_log_count'] == 1
    assert r2['execution_log_count'] == 2
    assert r3['execution_log_count'] == 3

    # read-back preserves the recorded sequence
    log = read_manifest('rec-order')[EXECUTION_LOG_KEY]
    assert [e['step_id'] for e in log] == ['verify:quality-gate', 'verify:module-tests', 'verify:coverage']
    assert [e['outcome'] for e in log] == ['executed', 'executed', 'skipped']


# =============================================================================
# Canonical step-key: --step-id is canonicalized before the row is appended
# =============================================================================
def test_record_step_id_containing_any_line_separator_rejected(plan_context):
    """Every line separator breaks the joined row, not just '\\n' — splitlines decides."""
    _compose('rec-step-id-sep')

    for bad_key in (
        'step\r\nid',
        'step\rid',
        'step\x0bid',
        'step\x0cid',
        'step' + chr(0x2028) + 'id',
        'step' + chr(0x2029) + 'id',
    ):
        result = cmd_record_step(_record_ns(plan_id='rec-step-id-sep', step_id=bad_key))

        assert result is not None, bad_key
        assert result['status'] == 'error', (bad_key, result)
        assert result['error'] == 'invalid_step_id', (bad_key, result)

    assert EXECUTION_LOG_KEY not in (read_manifest('rec-step-id-sep') or {})


def test_record_same_step_twice_appends_two_rows(plan_context):
    """The log is an ordered append log, not a keyed map — repeats append."""
    _compose('rec-dup')

    cmd_record_step(_record_ns(plan_id='rec-dup', step_id='verify:quality-gate', outcome='error'))
    result = cmd_record_step(_record_ns(plan_id='rec-dup', step_id='verify:quality-gate', outcome='executed'))

    assert result['execution_log_count'] == 2
    log = read_manifest('rec-dup')[EXECUTION_LOG_KEY]
    assert len(log) == 2
    assert log[0]['outcome'] == 'error'
    assert log[1]['outcome'] == 'executed'


def test_record_default_prefixed_step_id_stored_canonicalized(plan_context):
    """A ``default:``-prefixed --step-id is stored under the bare canonical key.

    The record-step handler routes --step-id through the shared
    canonicalize_step_key so execution-log keys reconcile with the manifest's
    phase-step keys.
    """
    _compose('rec-canon-default')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-canon-default',
            step_id='default:push',
            phase='6-finalize',
            outcome='executed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['step_id'] == 'push'
    entry = read_manifest('rec-canon-default')[EXECUTION_LOG_KEY][0]
    assert entry['step_id'] == 'push'


def test_record_promoted_alias_step_id_stored_bare(plan_context):
    """A promoted ``plan-marshall:automatic-review`` --step-id stores as bare ``automatic-review``."""
    _compose('rec-canon-promoted')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-canon-promoted',
            step_id='plan-marshall:automatic-review',
            phase='6-finalize',
            outcome='executed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['step_id'] == 'automatic-review'
    entry = read_manifest('rec-canon-promoted')[EXECUTION_LOG_KEY][0]
    assert entry['step_id'] == 'automatic-review'


def test_record_project_prefixed_step_id_preserved(plan_context):
    """A ``project:``-prefixed --step-id is preserved verbatim (not stripped to bare)."""
    _compose('rec-canon-project')

    result = cmd_record_step(
        _record_ns(
            plan_id='rec-canon-project',
            step_id='project:finalize-step-plugin-doctor',
            phase='6-finalize',
            outcome='executed',
        )
    )

    assert result is not None and result['status'] == 'success'
    assert result['step_id'] == 'project:finalize-step-plugin-doctor'
    entry = read_manifest('rec-canon-project')[EXECUTION_LOG_KEY][0]
    assert entry['step_id'] == 'project:finalize-step-plugin-doctor'


# =============================================================================
# Error / validation paths
# =============================================================================


def test_record_missing_manifest_returns_none_with_toon_error(plan_context, capsys):
    """record-step against a plan with no manifest emits file_not_found via TOON."""
    # no compose for this plan id.
    result = cmd_record_step(_record_ns(plan_id='rec-no-manifest'))

    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out


def test_record_invalid_phase_returns_error(plan_context):
    """An unknown phase is rejected with an invalid_phase error dict."""
    _compose('rec-bad-phase')

    result = cmd_record_step(_record_ns(plan_id='rec-bad-phase', phase='7-deploy'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    # No row written.
    assert EXECUTION_LOG_KEY not in (read_manifest('rec-bad-phase') or {})


def test_record_invalid_outcome_returns_error(plan_context):
    """An unknown outcome is rejected with an invalid_outcome error dict."""
    _compose('rec-bad-outcome')

    result = cmd_record_step(_record_ns(plan_id='rec-bad-outcome', outcome='maybe'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_outcome'
    assert EXECUTION_LOG_KEY not in (read_manifest('rec-bad-outcome') or {})


def test_record_step_id_containing_comma_rejected_before_any_write(plan_context):
    """The join key must reconcile with the positional-CSV boundary row: a comma is refused."""
    _compose('rec-step-id-comma')

    result = cmd_record_step(_record_ns(plan_id='rec-step-id-comma', step_id='step,a'))

    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_step_id'
    assert EXECUTION_LOG_KEY not in (read_manifest('rec-step-id-comma') or {})


def test_record_phase_validated_before_manifest_read(plan_context):
    """Phase validation fires even when no manifest exists (pure input guard)."""
    # no compose.
    result = cmd_record_step(_record_ns(plan_id='rec-guard', phase='nope'))

    assert result is not None
    assert result['error'] == 'invalid_phase'
