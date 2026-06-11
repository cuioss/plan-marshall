#!/usr/bin/env python3
"""Tests for the ``record-step`` subcommand of manage-execution-manifest.py.

The ``record-step`` subcommand appends per-step execution-log rows (outcome +
token attribution) to the manifest's ``execution_log[]`` section. These tests
cover:

- appending ``executed`` / ``skipped`` / ``error`` rows with token attribution;
- token-attribution fields defaulting to ``0`` when omitted;
- the ordered append-log semantics (re-recording the same step appends another
  row; reading back reflects the recorded sequence);
- ``execution_log_count`` tracking the running row count;
- the missing-manifest error path (TOON ``file_not_found``);
- input-validation rejection of an unknown phase / outcome;
- a CLI subprocess roundtrip exercising the executor plumbing.

Mirrors the tier-2 direct-import + CLI-subprocess split used by the sibling
``test_manage_execution_manifest_read.py`` / ``_validate.py`` suites.
"""

import importlib.util
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script

# Script path for subprocess (CLI plumbing) tests.
SCRIPT_PATH = get_script_path('plan-marshall', 'manage-execution-manifest', 'manage-execution-manifest.py')

# Tier 2 direct imports via importlib (scripts loaded via PYTHONPATH at runtime).
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None, f'Failed to load module spec for {filename}'
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_script', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_record_step = _mem.cmd_record_step
read_manifest = _mem.read_manifest
EXECUTION_LOG_KEY = _mem.EXECUTION_LOG_KEY
VALID_RECORD_PHASES = _mem.VALID_RECORD_PHASES
VALID_RECORD_OUTCOMES = _mem.VALID_RECORD_OUTCOMES
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Quiet down the best-effort decision-log writes so tests don't depend on a
# running executor / a resolvable plan log dir.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]
_mem._log_record_step = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace Helpers
# =============================================================================


def _compose_ns(
    plan_id: str = 'rec-plan',
    change_type: str = 'feature',
    track: str = 'complex',
    scope_estimate: str = 'multi_module',
    recipe_key: str | None = None,
    affected_files_count: int = 5,
    phase_5_steps: str | None = 'quality-gate,module-tests',
    phase_6_steps: str | None = ','.join(DEFAULT_PHASE_6_STEPS),
    commit_and_push: str | None = None,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track=track,
        scope_estimate=scope_estimate,
        recipe_key=recipe_key,
        affected_files_count=affected_files_count,
        phase_5_steps=phase_5_steps,
        phase_6_steps=phase_6_steps,
        commit_and_push=commit_and_push,
    )


def _record_ns(
    plan_id: str = 'rec-plan',
    step_id: str = 'quality_check',
    phase: str = '5-execute',
    outcome: str = 'executed',
    total_tokens: int = 0,
    tool_uses: int = 0,
    duration_ms: int = 0,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        step_id=step_id,
        phase=phase,
        outcome=outcome,
        total_tokens=total_tokens,
        tool_uses=tool_uses,
        duration_ms=duration_ms,
    )


def _compose(plan_id: str) -> None:
    """Materialize a manifest for ``plan_id`` (record-step requires one)."""
    cmd_compose(_compose_ns(plan_id=plan_id))


# =============================================================================
# Append + token-attribution tests
# =============================================================================


def test_record_executed_appends_row_with_token_attribution(plan_context):
    """An executed record appends one row carrying its token-attribution triple."""
    # Arrange
    _compose('rec-exec')

    # Act
    result = cmd_record_step(
        _record_ns(
            plan_id='rec-exec',
            step_id='quality_check',
            phase='5-execute',
            outcome='executed',
            total_tokens=1200,
            tool_uses=7,
            duration_ms=4200,
        )
    )

    # Assert
    assert result is not None
    assert result['status'] == 'success'
    assert result['recorded'] is True
    assert result['step_id'] == 'quality_check'
    assert result['phase'] == '5-execute'
    assert result['outcome'] == 'executed'
    assert result['total_tokens'] == 1200
    assert result['tool_uses'] == 7
    assert result['duration_ms'] == 4200
    assert result['execution_log_count'] == 1
    assert 'timestamp' in result


def test_record_executed_persists_row_to_manifest(plan_context):
    """The appended row is persisted into the manifest's execution_log section."""
    # Arrange
    _compose('rec-persist')

    # Act
    cmd_record_step(
        _record_ns(
            plan_id='rec-persist',
            step_id='build_verify',
            total_tokens=900,
            tool_uses=3,
            duration_ms=1500,
        )
    )

    # Assert
    manifest = read_manifest('rec-persist')
    assert manifest is not None
    log = manifest[EXECUTION_LOG_KEY]
    assert isinstance(log, list)
    assert len(log) == 1
    entry = log[0]
    assert entry['step_id'] == 'build_verify'
    assert entry['outcome'] == 'executed'
    assert entry['total_tokens'] == 900
    assert entry['tool_uses'] == 3
    assert entry['duration_ms'] == 1500
    assert 'timestamp' in entry


def test_record_skipped_appends_row(plan_context):
    """A skipped step records a row with the skipped outcome."""
    # Arrange
    _compose('rec-skip')

    # Act
    result = cmd_record_step(
        _record_ns(plan_id='rec-skip', step_id='coverage', outcome='skipped')
    )

    # Assert
    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'skipped'
    manifest = read_manifest('rec-skip')
    assert manifest is not None
    assert manifest[EXECUTION_LOG_KEY][0]['outcome'] == 'skipped'


def test_record_error_outcome_appends_row(plan_context):
    """An error step records a row with the error outcome."""
    # Arrange
    _compose('rec-error')

    # Act
    result = cmd_record_step(
        _record_ns(plan_id='rec-error', step_id='ci-verify', phase='6-finalize', outcome='error')
    )

    # Assert
    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'error'
    assert result['phase'] == '6-finalize'


def test_record_token_attribution_defaults_to_zero(plan_context):
    """Omitting the token-attribution flags records zeros, not missing columns."""
    # Arrange
    _compose('rec-zero')

    # Act
    result = cmd_record_step(_record_ns(plan_id='rec-zero', step_id='quality_check', outcome='skipped'))

    # Assert
    assert result is not None
    assert result['total_tokens'] == 0
    assert result['tool_uses'] == 0
    assert result['duration_ms'] == 0
    entry = read_manifest('rec-zero')[EXECUTION_LOG_KEY][0]
    assert entry['total_tokens'] == 0
    assert entry['tool_uses'] == 0
    assert entry['duration_ms'] == 0


def test_record_negative_token_values_clamped_to_zero(plan_context):
    """Negative attribution inputs are clamped to zero (max(0, ...))."""
    # Arrange
    _compose('rec-neg')

    # Act
    result = cmd_record_step(
        _record_ns(
            plan_id='rec-neg',
            step_id='quality_check',
            total_tokens=-50,
            tool_uses=-1,
            duration_ms=-999,
        )
    )

    # Assert
    assert result is not None
    assert result['total_tokens'] == 0
    assert result['tool_uses'] == 0
    assert result['duration_ms'] == 0


# =============================================================================
# Ordered append-log semantics
# =============================================================================


def test_record_appends_in_order_and_count_increments(plan_context):
    """Repeated records append rows deterministically; reading back reflects order."""
    # Arrange
    _compose('rec-order')

    # Act
    r1 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='quality_check', outcome='executed'))
    r2 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='build_verify', outcome='executed'))
    r3 = cmd_record_step(_record_ns(plan_id='rec-order', step_id='coverage', outcome='skipped'))

    # Assert — running count tracks the append log
    assert r1['execution_log_count'] == 1
    assert r2['execution_log_count'] == 2
    assert r3['execution_log_count'] == 3

    # Assert — read-back preserves the recorded sequence
    log = read_manifest('rec-order')[EXECUTION_LOG_KEY]
    assert [e['step_id'] for e in log] == ['quality_check', 'build_verify', 'coverage']
    assert [e['outcome'] for e in log] == ['executed', 'executed', 'skipped']


def test_record_same_step_twice_appends_two_rows(plan_context):
    """The log is an ordered append log, not a keyed map — repeats append."""
    # Arrange
    _compose('rec-dup')

    # Act
    cmd_record_step(_record_ns(plan_id='rec-dup', step_id='quality_check', outcome='error'))
    result = cmd_record_step(_record_ns(plan_id='rec-dup', step_id='quality_check', outcome='executed'))

    # Assert
    assert result['execution_log_count'] == 2
    log = read_manifest('rec-dup')[EXECUTION_LOG_KEY]
    assert len(log) == 2
    assert log[0]['outcome'] == 'error'
    assert log[1]['outcome'] == 'executed'


# =============================================================================
# Error / validation paths
# =============================================================================


def test_record_missing_manifest_returns_none_with_toon_error(plan_context, capsys):
    """record-step against a plan with no manifest emits file_not_found via TOON."""
    # Arrange — no compose for this plan id.
    # Act
    result = cmd_record_step(_record_ns(plan_id='rec-no-manifest'))

    # Assert
    assert result is None
    captured = capsys.readouterr()
    assert 'file_not_found' in captured.out


def test_record_invalid_phase_returns_error(plan_context):
    """An unknown phase is rejected with an invalid_phase error dict."""
    # Arrange
    _compose('rec-bad-phase')

    # Act
    result = cmd_record_step(_record_ns(plan_id='rec-bad-phase', phase='7-deploy'))

    # Assert
    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_phase'
    # No row written.
    assert EXECUTION_LOG_KEY not in (read_manifest('rec-bad-phase') or {})


def test_record_invalid_outcome_returns_error(plan_context):
    """An unknown outcome is rejected with an invalid_outcome error dict."""
    # Arrange
    _compose('rec-bad-outcome')

    # Act
    result = cmd_record_step(_record_ns(plan_id='rec-bad-outcome', outcome='maybe'))

    # Assert
    assert result is not None
    assert result['status'] == 'error'
    assert result['error'] == 'invalid_outcome'
    assert EXECUTION_LOG_KEY not in (read_manifest('rec-bad-outcome') or {})


def test_record_phase_validated_before_manifest_read(plan_context):
    """Phase validation fires even when no manifest exists (pure input guard)."""
    # Arrange — no compose.
    # Act
    result = cmd_record_step(_record_ns(plan_id='rec-guard', phase='nope'))

    # Assert
    assert result is not None
    assert result['error'] == 'invalid_phase'


def test_valid_record_enums_are_the_documented_sets(plan_context):
    """Guard the contract constants the record-step subcommand validates against."""
    assert VALID_RECORD_PHASES == ('5-execute', '6-finalize')
    assert VALID_RECORD_OUTCOMES == ('executed', 'skipped', 'error')


# =============================================================================
# CLI plumbing (subprocess) tests
# =============================================================================


def test_cli_record_step_roundtrip(plan_context):
    """record-step over the CLI appends a row and echoes the success TOON."""
    # Arrange — compose a manifest via the CLI so the subprocess sees it.
    compose = run_script(
        SCRIPT_PATH,
        'compose',
        '--plan-id',
        'cli-rec',
        '--change-type',
        'feature',
        '--track',
        'complex',
        '--scope-estimate',
        'multi_module',
        '--affected-files-count',
        '5',
    )
    assert compose.returncode == 0

    # Act
    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec',
        '--step-id',
        'quality_check',
        '--phase',
        '5-execute',
        '--outcome',
        'executed',
        '--total-tokens',
        '1500',
        '--tool-uses',
        '4',
        '--duration-ms',
        '2200',
    )

    # Assert
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'success'
    assert data['recorded'] is True
    assert data['step_id'] == 'quality_check'
    assert data['outcome'] == 'executed'
    assert data['total_tokens'] == 1500
    assert data['tool_uses'] == 4
    assert data['duration_ms'] == 2200
    assert data['execution_log_count'] == 1


def test_cli_record_step_missing_manifest_emits_toon_error(plan_context):
    """record-step over the CLI without a manifest emits file_not_found via TOON."""
    # Act
    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec-missing',
        '--step-id',
        'quality_check',
        '--phase',
        '5-execute',
        '--outcome',
        'executed',
    )

    # Assert — TOON contract: script exits 0 on missing-file errors.
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'file_not_found'
