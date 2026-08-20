#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Regression tests for the retired ``ceremony-policy`` manage-config verb (D9).

The ``ceremony-policy`` noun was retired from ``manage-config.py`` argparse and the
``_cmd_ceremony_policy.py`` handler deleted. Two auto-continuation knobs the verb
used to surface (``finalize_without_asking`` / ``loop_back_without_asking``) remain
flat fields under ``plan.phase-6-finalize``, read / written via the standard
``plan phase-6-finalize get/set --field <knob>`` access shape. The third
(``final_merge_without_asking``) is now a step-owned param nested under
``default:branch-cleanup`` in the keyed-map ``steps`` structure, read / written via
the one-stop ``plan phase-6-finalize step get/set --step-id default:branch-cleanup``
access shape.

This module pins the post-retirement contract:

1. ``manage-config ceremony-policy …`` is rejected by argparse (exit code 2) — the
   noun is gone from the ``subparsers`` choices.
2. The deleted handler script is absent from disk.
3. Each flat automation knob reads back through the new ``plan phase-6-finalize get``
   path with its migrated default, and the step-owned knob reads back through the
   ``step get`` path; all round-trip through their respective ``set`` shapes.
"""

# ruff: noqa: I001, E402

from argparse import Namespace
from conftest import get_script_path, get_scripts_dir, load_script_module, run_script


SCRIPT_PATH = get_script_path('plan-marshall', 'manage-config', 'manage-config.py')


_cmd_quality_phases_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_quality_phases.py', module_name='_cmd_quality_phases_for_verb_retirement_test'
)
_cmd_init_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_init.py', module_name='_cmd_init_for_verb_retirement_test'
)
_config_defaults_mod = load_script_module(
    'plan-marshall', 'manage-config', '_config_defaults.py', module_name='_config_defaults_for_verb_retirement_test'
)
_cmd_finalize_steps_mod = load_script_module(
    'plan-marshall', 'manage-config', '_cmd_finalize_steps.py', module_name='_cmd_finalize_steps_for_lane_ask_test'
)
cmd_list_ask_lane = _cmd_finalize_steps_mod.cmd_finalize_steps_list_ask_lane
cmd_set_lane = _cmd_finalize_steps_mod.cmd_finalize_steps_set_lane

# The two adversarial infra elements that seed with a lane:ask override.
_ASK_INFRA_STEPS = ('plan-marshall:automatic-review', 'default:sonar-roundtrip')

# Import shared infrastructure (conftest.py sets up PYTHONPATH).
import conftest  # noqa: E402, F401

# The two flat auto-continuation knobs that remain phase-level fields, with
# their migrated (preserved) defaults. final_merge_without_asking is NOT here —
# it moved into the default:branch-cleanup step's nested param object and is
# covered by the step-get tests below.
_MIGRATED_KNOBS = (
    ('finalize_without_asking', True),
    ('loop_back_without_asking', False),
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
    handler = get_scripts_dir('plan-marshall', 'manage-config') / '_cmd_ceremony_policy.py'
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


def test_final_merge_without_asking_reads_via_step_get(plan_context):
    """final_merge_without_asking reads back via ``step get`` on default:branch-cleanup with its default.

    The knob moved out of the flat phase-level fields into the
    default:branch-cleanup step's nested param object, so the fresh-config default
    surfaces through the one-stop ``step get`` verb, not ``get --field``.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(verb='step', step_verb='get', step_id='default:branch-cleanup'),
        'phase-6-finalize',
    )

    assert result['status'] == 'success'
    assert result['params']['final_merge_without_asking'] is False


def test_final_merge_without_asking_step_set_then_get_roundtrips(plan_context):
    """``step set --step-id default:branch-cleanup --param final_merge_without_asking --value true`` round-trips.

    Sets the knob to ``true`` (the non-default opt-in to merge without asking)
    so the round-trip proves persistence against a value distinct from the
    ``False`` default, via the one-stop step verb against the keyed map.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # set then get via the step verb
    set_result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(
            verb='step',
            step_verb='set',
            step_id='default:branch-cleanup',
            param='final_merge_without_asking',
            value='true',
        ),
        'phase-6-finalize',
    )
    get_result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(verb='step', step_verb='get', step_id='default:branch-cleanup'),
        'phase-6-finalize',
    )

    # bool coercion + persistence
    assert set_result['status'] == 'success'
    assert get_result['params']['final_merge_without_asking'] is True


def test_qgate_is_not_a_seeded_flat_finalize_field(plan_context):
    """``qgate`` is no longer a seeded flat phase-6-finalize field.

    The finalize `qgate` run-at-all gate was migrated onto the per-element
    ``steps[default:pre-push-quality-gate].lane`` override, so a fresh config carries no
    flat ``qgate`` field under ``plan.phase-6-finalize`` (the former flat
    ``set --field qgate`` / ``get --field qgate`` round-trip no longer applies —
    the gate rides the lane channel).
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))

    config = _config_defaults_mod.get_default_config()
    assert 'qgate' not in config['plan']['phase-6-finalize'], (
        'qgate must not survive as a flat phase-6-finalize field after the '
        'run-at-all → lane migration'
    )


def test_simplify_step_no_longer_declares_a_simplify_run_at_all_param(plan_context):
    """The simplify step no longer declares a ``simplify`` run-at-all param.

    The folded ``simplify`` run-at-all gate was removed in the ceremony
    run-at-all → lane migration: ``default:finalize-step-simplify`` is now
    config-less, and its on/off is governed by its ``steps.<step>.lane`` override
    rather than a step-owned ``simplify`` param.
    """
    from configurable_contract import resolve_step_defaults_optional

    _cmd_init_mod.cmd_init(Namespace(force=False))

    # the step declares no configurable params at all now (resolves to None/{}).
    resolved = resolve_step_defaults_optional('default:finalize-step-simplify') or {}
    assert 'simplify' not in resolved, (
        'default:finalize-step-simplify must no longer declare a simplify param'
    )

    # and the seeded step nested-param object is the empty {} (config-less).
    config = _config_defaults_mod.get_default_config()
    steps = config['plan']['phase-6-finalize']['steps']
    assert steps.get('default:finalize-step-simplify') == {}


# =============================================================================
# (D8) finalize-steps list-ask-lane / set-lane — the steward always-prompt verbs
#
# `list-ask-lane` enumerates the finalize steps whose lane override is still
# `ask` (the two seeded adversarial infra elements); `set-lane` persists the
# operator's resolved off/standard/full answer as the step's lane override. Together
# they back the marshall-steward mandatory prompt at setup + update-config.
# =============================================================================


def test_list_ask_lane_returns_the_two_seeded_infra_elements(plan_context):
    """A fresh config lists exactly the two lane:ask infra elements."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    result = cmd_list_ask_lane(Namespace())

    assert result['status'] == 'success'
    assert set(result['ask_steps']) == set(_ASK_INFRA_STEPS)
    assert result['ask_steps_count'] == 2


def test_set_lane_persists_off_and_resolves_the_ask(plan_context):
    """set-lane off persists the override and the element drops off the ask list."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    set_result = cmd_set_lane(
        Namespace(step_id='plan-marshall:automatic-review', lane='off')
    )
    assert set_result['status'] == 'success'
    assert set_result['step_id'] == 'plan-marshall:automatic-review'
    assert set_result['lane'] == 'off'

    # The resolved element is no longer ask-tier; only sonar-roundtrip remains.
    after = cmd_list_ask_lane(Namespace())
    assert after['ask_steps'] == ['default:sonar-roundtrip']

    # The persisted lane override reads back through the step-get verb.
    get_result = _cmd_quality_phases_mod.cmd_phase(
        Namespace(verb='step', step_verb='get', step_id='plan-marshall:automatic-review'),
        'phase-6-finalize',
    )
    assert get_result['status'] == 'success'
    assert get_result['params']['lane'] == 'off'


def test_set_lane_accepts_standard_and_full(plan_context):
    """set-lane accepts each resolved value (off/standard/full)."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    standard_result = cmd_set_lane(
        Namespace(step_id='default:sonar-roundtrip', lane='standard')
    )
    assert standard_result['status'] == 'success'
    assert standard_result['lane'] == 'standard'

    full_result = cmd_set_lane(
        Namespace(step_id='plan-marshall:automatic-review', lane='full')
    )
    assert full_result['status'] == 'success'
    assert full_result['lane'] == 'full'

    # Both are now resolved — the ask list is empty.
    after = cmd_list_ask_lane(Namespace())
    assert after['ask_steps'] == []
    assert after['ask_steps_count'] == 0


def test_set_lane_rejects_non_resolved_lane_values(plan_context):
    """set-lane rejects `ask` / `minimal` / bogus — only off/standard/full resolve an ask."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    for bad in ('ask', 'minimal', 'bogus', ''):
        result = cmd_set_lane(
            Namespace(step_id='plan-marshall:automatic-review', lane=bad)
        )
        assert result['status'] == 'error', f'lane={bad!r} must be rejected'


def test_set_lane_rejects_unknown_step_id(plan_context):
    """set-lane rejects a step id outside the discovered finalize-step universe."""
    _cmd_init_mod.cmd_init(Namespace(force=False))

    result = cmd_set_lane(
        Namespace(step_id='default:does-not-exist', lane='off')
    )
    assert result['status'] == 'error'


def test_finalize_steps_list_ask_lane_cli_is_recognized():
    """`manage-config finalize-steps list-ask-lane` is a registered subcommand (not argparse-rejected)."""
    result = run_script(SCRIPT_PATH, 'finalize-steps', 'list-ask-lane')
    # Recognized subcommand → NOT an argparse exit-2 rejection.
    assert result.returncode != 2, (
        'finalize-steps list-ask-lane must be a registered subcommand'
    )


def test_finalize_steps_set_lane_cli_rejects_invalid_lane_choice():
    """`finalize-steps set-lane --lane bogus` → HANDLER rejection naming the route.

    The refusal moved off argparse ``choices=`` and into the handler so it can
    route a caller to the verb that DOES write the value they asked for. That
    matters for ``minimal`` / ``ask``, which the composer honours; a bogus value
    takes the same path and still gets told where lane values are written. The
    contract asserted here is the emitted ``status: error``, not the exit code —
    ``main`` returns 0 after printing any result, so every manage-config
    validation error rides that channel. See
    ``test_finalize_steps_lane_rejection.py`` for the full rejection contract.
    """
    result = run_script(
        SCRIPT_PATH, 'finalize-steps', 'set-lane', '--step-id', 'plan-marshall:automatic-review', '--lane', 'bogus'
    )
    combined = f'{result.stdout}\n{result.stderr}'
    assert 'invalid choice' not in combined, (
        'argparse rejected --lane before the handler ran, so no routing message reaches the caller'
    )
    assert 'status: error' in combined, 'a refused write must not report success'
    assert "invalid lane 'bogus'" in combined
    assert 'step set' in combined, 'the rejection must name the verb that writes lane values'


def test_finalize_steps_set_lane_cli_requires_step_id_and_lane():
    """`finalize-steps set-lane` with no args → argparse required-arg rejection (exit 2)."""
    result = run_script(SCRIPT_PATH, 'finalize-steps', 'set-lane')
    assert result.returncode == 2, 'set-lane requires --step-id and --lane'
