#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the sync-defaults command in manage-config.

Covers the non-destructive deep-merge contract:
- empty marshal.json gains all defaults
- user-set keys are preserved while missing ones are added
- deeply-nested missing sub-keys are added (including the keyed-map step structure)
- idempotency (re-running adds nothing)
- TOON output enumerates added dotted paths correctly
"""

# ruff: noqa: I001, E402

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

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


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_sync_mod = _load_module('_cmd_sync_defaults', '_cmd_sync_defaults.py')

cmd_sync_defaults = _sync_mod.cmd_sync_defaults


# =============================================================================
# Keyed-map serial-form helpers
# =============================================================================
#
# `plan.phase-6-finalize.steps` and `plan.phase-5-execute.verification_steps`
# serialize on disk as the canonical keyed map: an id-keyed object
# `{step_id: {params}}` (`{}` for a config-less step). The default seed is
# therefore a dict, which the deep-merge recurses into: a present step key keeps
# its value while missing sibling step keys (and missing per-step params) are
# back-filled from the default keyed map.


def _params_for(steps_map: dict, step_id: str):
    """Return a step's params from a keyed-map steps object.

    Returns the step's nested param object (``{}`` for a config-less step).
    Raises ``KeyError`` when the step id is absent.
    """
    return steps_map[step_id]


def _write_marshal(fixture_dir: Path, config: dict) -> Path:
    marshal_path = fixture_dir / 'marshal.json'
    marshal_path.parent.mkdir(parents=True, exist_ok=True)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')
    return marshal_path


def _read_marshal(fixture_dir: Path) -> dict:
    return json.loads((fixture_dir / 'marshal.json').read_text(encoding='utf-8'))


def test_sync_defaults_errors_when_uninitialized(plan_context):
    """sync-defaults fails cleanly when marshal.json does not exist."""
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'error'
    assert 'marshal.json' in result['error'].lower()


def test_sync_defaults_empty_marshal_gains_all_defaults(plan_context):
    """An empty marshal.json gains every key present in get_default_config()."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    assert result['added_count'] > 0
    config = _read_marshal(plan_context.fixture_dir)
    # the steps default is the keyed-map form; auto_rebase_threshold nests in
    # the nested param object for default:branch-cleanup
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    assert config['project']['default_base_branch'] == 'main'
    # Top-level default keys are added
    assert 'plan' in result['added']
    assert 'project' in result['added']


def test_sync_defaults_preserves_user_set_param_in_keyed_map(plan_context):
    """A user-set per-step param survives the sync; missing siblings are back-filled.

    The steps default is the keyed map, which the deep-merge recurses into: a
    present step key keeps its pinned param, while missing sibling params (and
    missing sibling steps) are back-filled from the default keyed map.
    """
    # user pinned pr_merge_strategy on the branch-cleanup step
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:branch-cleanup': {'pr_merge_strategy': 'merge'}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    # the user's pinned param survives the deep-merge
    assert branch_cleanup['pr_merge_strategy'] == 'merge'
    # the missing sibling param is back-filled from the default keyed map
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    # the per-step dotted path is reported for the back-filled sibling
    assert 'plan.phase-6-finalize.steps.default:branch-cleanup.auto_rebase_threshold' in result['added']


def test_sync_defaults_preserves_user_set_true_in_keyed_map(plan_context):
    """A user-set True survives even though the default value is False (keyed-map merge).

    final_merge_without_asking is a nested param of default:branch-cleanup in the
    keyed map. The deep-merge preserves the present param key, so an explicit True
    survives the False default.
    """
    # user explicitly opted into merge-without-asking (default is False)
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:branch-cleanup': {'final_merge_without_asking': True}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the user's True override survives the deep-merge
    assert _params_for(steps, 'default:branch-cleanup')['final_merge_without_asking'] is True
    # the present param key is not re-added
    assert 'plan.phase-6-finalize.steps.default:branch-cleanup.final_merge_without_asking' not in result['added']


def test_sync_defaults_deep_merges_missing_siblings_into_keyed_map_steps(plan_context):
    """The default keyed map deep-merges missing siblings into a present user keyed map.

    Under the keyed-map merge, a user `steps` map that omits a sibling param gets
    it back-filled from the default — the merge recurses into the keyed map. This
    pins the behavioral consequence of restoring the keyed-map form (the LIST
    atomic-merge is gone).
    """
    # the branch-cleanup step is present but lacks auto_rebase_threshold
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:branch-cleanup': {'pr_merge_strategy': 'squash'}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    branch_cleanup = _params_for(steps, 'default:branch-cleanup')
    assert branch_cleanup['pr_merge_strategy'] == 'squash'
    # the missing sibling IS back-filled — the keyed map recurses per-step
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    assert 'plan.phase-6-finalize.steps.default:branch-cleanup.auto_rebase_threshold' in result['added']


def test_sync_defaults_backfills_missing_steps_into_pruned_keyed_map(plan_context):
    """A user's pruned single-entry steps map gains the missing default steps.

    The schema default is the keyed map, and the deep-merge recurses into it, so a
    user who pruned steps to a single entry gets the missing default step keys
    back-filled (each as a new top-level step key).
    """
    # user pruned the finalize steps to a single config-less entry
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:push': {}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)
    # the user's pruned entry survives
    assert 'default:push' in steps
    # a missing default step is back-filled and reported as a new step key
    assert 'default:archive-plan' in steps
    assert 'plan.phase-6-finalize.steps.default:archive-plan' in result['added']


def test_sync_defaults_is_idempotent(plan_context):
    """Re-running sync-defaults immediately produces an empty added list."""
    _write_marshal(plan_context.fixture_dir, {})
    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'
    assert first['added_count'] > 0

    # second run
    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert second['status'] == 'success'
    assert second['added'] == []
    assert second['added_count'] == 0


def test_sync_defaults_reports_added_paths_sorted(plan_context):
    """The TOON report enumerates added dotted paths in sorted order."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    assert result['added'] == sorted(result['added'])
    assert result['added_count'] == len(result['added'])


# =============================================================================
# Keyed-map back-fill on sync (steps / verification_steps copied as a keyed map)
# =============================================================================
#
# The steps / verification_steps defaults are the keyed-map form (`{}` for
# config-less steps, a non-empty param object for param-owning steps). When the
# whole `plan` block is absent, the default keyed map is copied wholesale under
# the top-level `plan` path. Config-less steps land as `{}`; param-owning steps
# land with their nested param object.


def test_sync_defaults_backfills_verification_steps_as_keyed_map(plan_context):
    """Syncing an empty marshal.json back-fills verification_steps as a keyed map of {}."""
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    # the whole keyed map is copied; config-less verify steps map to {}
    assert isinstance(verification_steps, dict)
    assert verification_steps, 'verification_steps backfill should not be empty'
    assert all(params == {} for params in verification_steps.values()), (
        f'config-less verify steps must map to {{}}, got {verification_steps!r}'
    )


def test_sync_defaults_backfills_finalize_steps_as_keyed_map_form(plan_context):
    """Syncing an empty marshal.json back-fills finalize steps as the keyed-map form.

    Param-owning steps (sonar-roundtrip / automated-review / branch-cleanup /
    finalize-step-simplify / finalize-step-preference-emitter) land with a
    non-empty nested param object; the remaining config-less steps map to {}.
    """
    _write_marshal(plan_context.fixture_dir, {})

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    assert isinstance(steps, dict)

    param_owning = {
        'default:sonar-roundtrip',
        'default:automated-review',
        'default:branch-cleanup',
        # default:finalize-step-simplify owns the folded `simplify` run-at-all gate
        'default:finalize-step-simplify',
        # default:finalize-step-preference-emitter owns the preference_min_recurrence knob
        'default:finalize-step-preference-emitter',
    }
    for step_id, params in steps.items():
        assert isinstance(params, dict), f'every step value must be a dict; got {params!r}'
        if step_id in param_owning:
            assert params, f'param-owning step {step_id!r} must carry a non-empty nested dict'
        else:
            assert params == {}, f'config-less step {step_id!r} must map to {{}}, got {params!r}'
    assert param_owning <= set(steps), (
        f'all param-owning steps must appear in the keyed map; '
        f'missing: {param_owning - set(steps)!r}'
    )


def test_sync_defaults_preserves_present_steps_map_untouched(plan_context):
    """A present `steps` map's existing keys are preserved; missing default keys are back-filled.

    The deep-merge recurses into a present keyed map: a user-supplied step key is
    preserved verbatim, while every missing default step key is back-filled.
    """
    # a marshal.json whose finalize steps already carry a pruned keyed map
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': {'default:create-pr': {}}}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    steps = config['plan']['phase-6-finalize']['steps']
    # the pre-existing entry is preserved
    assert 'default:create-pr' in steps
    # the present step key is NOT reported as added
    assert 'plan.phase-6-finalize.steps.default:create-pr' not in result['added']
    # a missing default step key IS back-filled
    assert 'default:archive-plan' in steps


def test_sync_defaults_is_idempotent_against_keyed_map_steps(plan_context):
    """A second sync adds nothing — the keyed-map back-fill is idempotent.

    The first sync copies the default keyed map; the second observes the
    `steps` / `verification_steps` keys already present and re-adds nothing,
    proving the merge is stable against the keyed map it just wrote.
    """
    _write_marshal(plan_context.fixture_dir, {})
    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'

    # second run observes the back-filled keyed map and adds nothing
    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert second['status'] == 'success'
    assert second['added'] == []
    assert second['added_count'] == 0
    # the verify steps remain the keyed map of {} after the idempotent re-sync
    config = _read_marshal(plan_context.fixture_dir)
    verification_steps = config['plan']['phase-5-execute']['verification_steps']
    assert isinstance(verification_steps, dict)
    assert all(params == {} for params in verification_steps.values())
