#!/usr/bin/env python3
"""Regression tests for the retired ``ceremony-policy`` manage-config verb (D9).

The ``ceremony-policy`` noun was retired from ``manage-config.py`` argparse and the
``_cmd_ceremony_policy.py`` handler deleted. The three auto-continuation knobs the
verb used to surface (``finalize_without_asking`` / ``loop_back_without_asking`` /
``final_merge_without_asking``) are now flat fields under ``plan.phase-6-finalize``, read /
written via the standard ``plan phase-6-finalize get/set --field <knob>`` access shape.

This module pins the post-retirement contract:

1. ``manage-config ceremony-policy …`` is rejected by argparse (exit code 2) — the
   noun is gone from the ``subparsers`` choices.
2. The deleted handler script is absent from disk.
3. Each automation knob reads back through the new ``plan phase-6-finalize get``
   path with its migrated default, and round-trips through ``set``.
"""

# ruff: noqa: I001, E402

import importlib.util
import sys
from argparse import Namespace
from pathlib import Path

from conftest import get_script_path, run_script  # type: ignore[import-not-found]

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

SCRIPT_PATH = get_script_path('plan-marshall', 'manage-config', 'manage-config.py')


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_quality_phases_mod = _load_module(
    '_cmd_quality_phases_for_verb_retirement_test', '_cmd_quality_phases.py'
)
_cmd_init_mod = _load_module('_cmd_init_for_verb_retirement_test', '_cmd_init.py')

# Import shared infrastructure (conftest.py sets up PYTHONPATH).
import conftest  # noqa: E402, F401

# The three auto-continuation knobs with their migrated (preserved) defaults.
_MIGRATED_KNOBS = (
    ('finalize_without_asking', True),
    ('loop_back_without_asking', False),
    ('final_merge_without_asking', False),
)


# =============================================================================
# (1) The ceremony-policy verb is rejected by argparse
# =============================================================================


def test_ceremony_policy_get_verb_is_rejected():
    """``manage-config ceremony-policy get`` → argparse rejection (exit 2)."""
    result = run_script(SCRIPT_PATH, 'ceremony-policy', 'get', '--field', 'automation.finalize_without_asking')
    assert result.returncode == 2, (
        'ceremony-policy must be an invalid noun after retirement (argparse exit 2)'
    )
    assert 'invalid choice' in result.stderr or 'ceremony-policy' in result.stderr


def test_ceremony_policy_set_verb_is_rejected():
    """``manage-config ceremony-policy set`` → argparse rejection (exit 2)."""
    result = run_script(
        SCRIPT_PATH, 'ceremony-policy', 'set', '--field', 'finalize.qgate', '--value', 'never'
    )
    assert result.returncode == 2, (
        'ceremony-policy set must be rejected by argparse after retirement'
    )


def test_ceremony_policy_handler_script_is_deleted():
    """The ``_cmd_ceremony_policy.py`` handler must be absent from disk."""
    handler = _SCRIPTS_DIR / '_cmd_ceremony_policy.py'
    assert not handler.exists(), (
        '_cmd_ceremony_policy.py must be deleted after the ceremony_policy dissolution'
    )


# =============================================================================
# (2) Automation knobs read via the new plan phase-6-finalize get path
# =============================================================================


def test_each_automation_knob_reads_via_phase_get(plan_context):
    """Each migrated knob reads back through ``plan phase-6-finalize get`` with its default."""
    # fresh marshal.json (no overrides → default merge)
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # each knob resolves to its migrated default via the phase get path
    for knob, expected in _MIGRATED_KNOBS:
        result = _cmd_quality_phases_mod.cmd_phase(
            Namespace(verb='get', field=knob), 'phase-6-finalize'
        )
        assert result['status'] == 'success', f'{knob} must resolve'
        assert result['value'] is expected, f'{knob} default must be {expected}'


def test_automation_knob_set_then_get_roundtrips(plan_context):
    """``plan phase-6-finalize set --field final_merge_without_asking --value true`` round-trips.

    Sets the knob to ``true`` (the non-default opt-in to merge without asking)
    so the round-trip proves persistence against a value distinct from the
    ``False`` default.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # set then get
    set_result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(verb='set', field='final_merge_without_asking', value='true'), 'phase-6-finalize'
    )
    get_result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(verb='get', field='final_merge_without_asking'), 'phase-6-finalize'
    )

    # bool coercion + persistence
    assert set_result['status'] == 'success'
    assert get_result['value'] is True


def test_run_at_all_gate_set_then_get_roundtrips(plan_context):
    """``plan phase-6-finalize set --field self_review --value always`` round-trips."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(verb='set', field='self_review', value='always'), 'phase-6-finalize'
    )
    get_result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(verb='get', field='self_review'), 'phase-6-finalize'
    )

    assert set_result['status'] == 'success'
    assert set_result['value'] == 'always'
    assert get_result['value'] == 'always'
