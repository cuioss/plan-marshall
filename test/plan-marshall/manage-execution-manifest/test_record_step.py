#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
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

# Step-ownership routing primitives live in _manifest_core (loaded directly:
# the hyphenated entry does not re-export them). See the "Step ownership"
# section in _manifest_core.py.
_core = _load_module('_mem_core', '_manifest_core.py')
owner_of = _core.owner_of
is_leaf_dispatchable = _core.is_leaf_dispatchable
validate_step_owner = _core.validate_step_owner
VALID_STEP_OWNERS = _core.VALID_STEP_OWNERS
DEFAULT_STEP_OWNER = _core.DEFAULT_STEP_OWNER
ORCHESTRATOR_OWNED_STEPS = _core.ORCHESTRATOR_OWNED_STEPS

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
    step_id: str = 'verify:quality-gate',
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

    result = cmd_record_step(
        _record_ns(plan_id='rec-skip', step_id='verify:coverage', outcome='skipped')
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'skipped'
    manifest = read_manifest('rec-skip')
    assert manifest is not None
    assert manifest[EXECUTION_LOG_KEY][0]['outcome'] == 'skipped'


def test_record_error_outcome_appends_row(plan_context):
    """An error step records a row with the error outcome."""
    _compose('rec-error')

    result = cmd_record_step(
        _record_ns(plan_id='rec-error', step_id='ci-verify', phase='6-finalize', outcome='error')
    )

    assert result is not None and result['status'] == 'success'
    assert result['outcome'] == 'error'
    assert result['phase'] == '6-finalize'


def test_record_token_attribution_defaults_to_zero(plan_context):
    """Omitting the token-attribution flags records zeros, not missing columns."""
    _compose('rec-zero')

    result = cmd_record_step(_record_ns(plan_id='rec-zero', step_id='verify:quality-gate', outcome='skipped'))

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


def test_record_phase_validated_before_manifest_read(plan_context):
    """Phase validation fires even when no manifest exists (pure input guard)."""
    # no compose.
    result = cmd_record_step(_record_ns(plan_id='rec-guard', phase='nope'))

    assert result is not None
    assert result['error'] == 'invalid_phase'


def test_valid_record_enums_are_the_documented_sets(plan_context):
    """Guard the contract constants the record-step subcommand validates against."""
    assert VALID_RECORD_PHASES == ('5-execute', '6-finalize')
    assert VALID_RECORD_OUTCOMES == ('executed', 'skipped', 'error')


# =============================================================================
# Step-ownership routing (orchestrator-owned vs leaf-dispatchable)
# =============================================================================


def test_valid_step_owners_vocabulary():
    """The declared owner vocabulary is the closed two-value set."""
    assert VALID_STEP_OWNERS == ('orchestrator-owned', 'leaf-dispatchable')
    assert DEFAULT_STEP_OWNER == 'leaf-dispatchable'


def test_validate_step_owner_accepts_declared_and_rejects_unknown():
    """validate_step_owner is a membership predicate over VALID_STEP_OWNERS."""
    assert validate_step_owner('orchestrator-owned') is True
    assert validate_step_owner('leaf-dispatchable') is True
    assert validate_step_owner('main-only') is False
    assert validate_step_owner('') is False


def test_owner_of_sub_dispatching_steps_are_orchestrator_owned():
    """The known sub-dispatching finalize steps resolve to orchestrator-owned."""
    for step in (
        'finalize-step-plugin-doctor',
        'finalize-step-pre-submission-self-review',
        'automatic-review',
        'finalize-step-simplify',
    ):
        assert owner_of(step) == 'orchestrator-owned', step
        assert step in ORCHESTRATOR_OWNED_STEPS


def test_owner_of_strips_default_and_project_prefixes():
    """default:- and project:-prefixed spellings classify identically to the bare name."""
    assert owner_of('project:finalize-step-plugin-doctor') == 'orchestrator-owned'
    assert owner_of('project:finalize-step-pre-submission-self-review') == 'orchestrator-owned'
    assert owner_of('default:finalize-step-simplify') == 'orchestrator-owned'


def test_owner_of_defaults_leaf_dispatchable():
    """Steps not in the registry default to leaf-dispatchable."""
    for step in ('push', 'create-pr', 'ci-verify', 'verify:quality-gate', 'archive-plan'):
        assert owner_of(step) == 'leaf-dispatchable', step


def test_is_leaf_dispatchable_rejects_orchestrator_owned_step():
    """A dispatched leaf must never be handed an orchestrator-owned step."""
    assert is_leaf_dispatchable('project:finalize-step-plugin-doctor') is False
    assert is_leaf_dispatchable('automatic-review') is False
    # A leaf-dispatchable step is accepted.
    assert is_leaf_dispatchable('push') is True
    assert is_leaf_dispatchable('verify:quality-gate') is True


# =============================================================================
# CLI plumbing (subprocess) tests
# =============================================================================


def test_cli_record_step_roundtrip(plan_context):
    """record-step over the CLI appends a row and echoes the success TOON."""
    # compose a manifest via the CLI so the subprocess sees it.
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

    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec',
        '--step-id',
        'verify:quality-gate',
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

    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'success'
    assert data['recorded'] is True
    assert data['step_id'] == 'verify:quality-gate'
    assert data['outcome'] == 'executed'
    assert data['total_tokens'] == 1500
    assert data['tool_uses'] == 4
    assert data['duration_ms'] == 2200
    assert data['execution_log_count'] == 1


def test_cli_record_step_missing_manifest_emits_toon_error(plan_context):
    """record-step over the CLI without a manifest emits file_not_found via TOON."""
    result = run_script(
        SCRIPT_PATH,
        'record-step',
        '--plan-id',
        'cli-rec-missing',
        '--step-id',
        'verify:quality-gate',
        '--phase',
        '5-execute',
        '--outcome',
        'executed',
    )

    # TOON contract: script exits 0 on missing-file errors.
    assert result.returncode == 0
    data = result.toon()
    assert data['status'] == 'error'
    assert data['error'] == 'file_not_found'
