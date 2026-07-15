#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for probe-backed ``use_merge_queue`` set-time validation (deliverable 4).

The ``step set`` path for ``default:branch-cleanup``'s ``use_merge_queue`` param
runs a live ``ci repo merge-queue probe`` when enabling and rejects the set (with
an actionable both-remedies message) unless the probe reports an eligible state.
The probe is isolated behind ``_run_merge_queue_probe`` so tests monkeypatch the
discriminator without shelling out.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import create_marshal_json

_MANAGE_CONFIG_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_MANAGE_CONFIG_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_MANAGE_CONFIG_SCRIPTS_DIR))


def _load_module(name: str, filename: str, scripts_dir: Path):
    spec = importlib.util.spec_from_file_location(name, scripts_dir / filename)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_qp = _load_module('_cmd_quality_phases', '_cmd_quality_phases.py', _MANAGE_CONFIG_SCRIPTS_DIR)


def _probe(**fields):
    """Build a probe helper returning a fixed dict."""
    return lambda: dict(fields)


# =============================================================================
# _validate_use_merge_queue — permit / reject per discriminator
# =============================================================================


def test_validate_permits_eligible_configured(monkeypatch):
    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _probe(status='success', eligibility='eligible_configured'))
    assert _qp._validate_use_merge_queue(True) is None


def test_validate_permits_eligible_unconfigured(monkeypatch):
    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _probe(status='success', eligibility='eligible_unconfigured'))
    assert _qp._validate_use_merge_queue(True) is None


def test_validate_rejects_ineligible_with_both_remedies(monkeypatch):
    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _probe(status='success', eligibility='ineligible'))
    err = _qp._validate_use_merge_queue(True)
    assert err is not None
    lowered = err.lower()
    # Names BOTH remedies — disable, and the steward provisioning step.
    assert 'disable use_merge_queue' in lowered
    assert 'merge-queue provisioning' in lowered or 'merge queue' in lowered
    assert 'ineligible' in lowered


def test_validate_rejects_unsupported(monkeypatch):
    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _probe(status='success', eligibility='unsupported'))
    err = _qp._validate_use_merge_queue(True)
    assert err is not None
    assert 'unsupported' in err.lower()


def test_validate_auth_scope_failure_returns_actionable_error(monkeypatch):
    # An auth-scope probe failure (status: error) must yield the actionable error,
    # never a stack trace.
    monkeypatch.setattr(
        _qp,
        '_run_merge_queue_probe',
        _probe(status='error', error='the gh token lacks the scope to read repository rulesets'),
    )
    err = _qp._validate_use_merge_queue(True)
    assert err is not None
    lowered = err.lower()
    assert 'scope' in lowered
    assert 'disable use_merge_queue' in lowered


def test_validate_disabling_is_always_permitted(monkeypatch):
    # Disabling (value False) must NOT probe and must always be permitted.
    def _boom():
        raise AssertionError('probe must not run when disabling use_merge_queue')

    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _boom)
    assert _qp._validate_use_merge_queue(False) is None


def test_validate_non_bool_value_is_permitted(monkeypatch):
    # A non-True value (e.g. a stray string) is not the enable path — no probe.
    def _boom():
        raise AssertionError('probe must not run for a non-True value')

    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _boom)
    assert _qp._validate_use_merge_queue('true-ish') is None


# =============================================================================
# _run_merge_queue_probe — subprocess degradation (never raises)
# =============================================================================


def test_run_probe_degrades_on_subprocess_error(monkeypatch):
    import subprocess

    def _raise(*a, **k):
        raise OSError('no executor')

    monkeypatch.setattr(subprocess, 'run', _raise)
    result = _qp._run_merge_queue_probe()
    assert result['status'] == 'error'


def test_run_probe_degrades_on_nonzero_exit(monkeypatch):
    import subprocess

    class _Result:
        returncode = 1
        stdout = ''
        stderr = 'boom'

    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: _Result())
    result = _qp._run_merge_queue_probe()
    assert result['status'] == 'error'


# =============================================================================
# Integration — the step set path enforces the validation
# =============================================================================


def _seed_branch_cleanup_step(fixture_dir: Path) -> None:
    """Ensure phase-6-finalize.steps carries default:branch-cleanup so `step set` finds it."""
    path = fixture_dir / 'marshal.json'
    config = json.loads(path.read_text(encoding='utf-8'))
    plan = config.setdefault('plan', {})
    phase = plan.setdefault('phase-6-finalize', {})
    steps = phase.get('steps')
    if not isinstance(steps, dict):
        steps = {}
    steps['default:branch-cleanup'] = steps.get('default:branch-cleanup', {})
    phase['steps'] = steps
    plan['phase-6-finalize'] = phase
    config['plan'] = plan
    path.write_text(json.dumps(config), encoding='utf-8')


def _step_set_ns(value: str) -> Namespace:
    return Namespace(
        sub_noun='phase-6-finalize',
        verb='step',
        step_verb='set',
        step_id='default:branch-cleanup',
        param='use_merge_queue',
        value=value,
    )


def test_step_set_rejects_enable_on_ineligible(monkeypatch, plan_context):
    create_marshal_json(plan_context.fixture_dir)
    _seed_branch_cleanup_step(plan_context.fixture_dir)
    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _probe(status='success', eligibility='ineligible'))

    result = _qp.cmd_phase(_step_set_ns('true'), 'phase-6-finalize')

    assert result['status'] == 'error'
    assert 'disable use_merge_queue' in result['error'].lower()
    # The rejected set was NOT persisted.
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text(encoding='utf-8'))
    params = config['plan']['phase-6-finalize']['steps']['default:branch-cleanup']
    assert params.get('use_merge_queue') is not True


def test_step_set_permits_enable_on_eligible_and_persists(monkeypatch, plan_context):
    create_marshal_json(plan_context.fixture_dir)
    _seed_branch_cleanup_step(plan_context.fixture_dir)
    monkeypatch.setattr(
        _qp, '_run_merge_queue_probe', _probe(status='success', eligibility='eligible_configured')
    )

    result = _qp.cmd_phase(_step_set_ns('true'), 'phase-6-finalize')

    assert result['status'] == 'success'
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text(encoding='utf-8'))
    params = config['plan']['phase-6-finalize']['steps']['default:branch-cleanup']
    assert params['use_merge_queue'] is True


def test_step_set_disable_does_not_probe(monkeypatch, plan_context):
    create_marshal_json(plan_context.fixture_dir)
    _seed_branch_cleanup_step(plan_context.fixture_dir)

    def _boom():
        raise AssertionError('disabling must not trigger a probe')

    monkeypatch.setattr(_qp, '_run_merge_queue_probe', _boom)

    result = _qp.cmd_phase(_step_set_ns('false'), 'phase-6-finalize')
    assert result['status'] == 'success'
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text(encoding='utf-8'))
    params = config['plan']['phase-6-finalize']['steps']['default:branch-cleanup']
    assert params['use_merge_queue'] is False
