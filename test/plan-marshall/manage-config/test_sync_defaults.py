#!/usr/bin/env python3
"""Tests for the sync-defaults command in manage-config.

Covers the non-destructive deep-merge contract:
- empty marshal.json gains all defaults
- user-set keys are preserved while missing ones are added
- deeply-nested missing sub-keys are added
- lists are treated as atomic (user's list survives)
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
    # auto_rebase_threshold nests under steps[default:branch-cleanup] (keyed map)
    branch_cleanup = config['plan']['phase-6-finalize']['steps']['default:branch-cleanup']
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    assert config['project']['default_base_branch'] == 'main'
    # Top-level default keys are added
    assert 'plan' in result['added']
    assert 'project' in result['added']


def test_sync_defaults_preserves_user_set_nested_step_param(plan_context):
    """A user-set nested step param survives the sync; missing siblings are added.

    pr_merge_strategy is now a nested param under steps[default:branch-cleanup].
    The deep-merge recurses into the keyed-map steps dict and the step's nested
    param object, preserving the user override while adding missing siblings.
    """
    # user pinned pr_merge_strategy to a non-default value (nested under its step)
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {'default:branch-cleanup': {'pr_merge_strategy': 'merge'}}
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    branch_cleanup = config['plan']['phase-6-finalize']['steps']['default:branch-cleanup']
    # User override preserved (default would be 'squash')
    assert branch_cleanup['pr_merge_strategy'] == 'merge'
    # Missing nested sibling added
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    # The preserved key is NOT reported as added
    assert (
        'plan.phase-6-finalize.steps.default:branch-cleanup.pr_merge_strategy'
        not in result['added']
    )
    # The missing nested sibling IS reported as added
    assert (
        'plan.phase-6-finalize.steps.default:branch-cleanup.auto_rebase_threshold'
        in result['added']
    )


def test_sync_defaults_preserves_user_set_true(plan_context):
    """A user-set True survives even though the default value is False.

    final_merge_without_asking is a nested param under steps[default:branch-cleanup];
    the deep-merge contract preserves a user override by key-existence (no value
    comparison), so an explicit True survives the False default and is not
    reported as added.
    """
    # user explicitly opted into merge-without-asking (default is False), nested
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {'default:branch-cleanup': {'final_merge_without_asking': True}}
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # present means "key exists"; no value comparison, no re-add
    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    branch_cleanup = config['plan']['phase-6-finalize']['steps']['default:branch-cleanup']
    assert branch_cleanup['final_merge_without_asking'] is True
    assert (
        'plan.phase-6-finalize.steps.default:branch-cleanup.final_merge_without_asking'
        not in result['added']
    )


def test_sync_defaults_adds_deeply_nested_missing_step_param(plan_context):
    """A missing nested step param is added when its owning step dict already exists."""
    # the branch-cleanup step exists but lacks auto_rebase_threshold
    _write_marshal(
        plan_context.fixture_dir,
        {
            'plan': {
                'phase-6-finalize': {
                    'steps': {'default:branch-cleanup': {'pr_merge_strategy': 'squash'}}
                }
            }
        },
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    branch_cleanup = config['plan']['phase-6-finalize']['steps']['default:branch-cleanup']
    assert branch_cleanup['pr_merge_strategy'] == 'squash'
    assert branch_cleanup['auto_rebase_threshold'] == 'no_overlap_only'
    assert (
        'plan.phase-6-finalize.steps.default:branch-cleanup.auto_rebase_threshold'
        in result['added']
    )


def test_sync_defaults_list_steps_are_atomic(plan_context):
    """A user's list-shaped steps value is kept verbatim (lists are atomic).

    Although the schema default is now a keyed map, the deep-merge treats a
    user-supplied list value as atomic (no dict recursion against a list), so a
    user who pruned steps to a flat list keeps it verbatim and the keyed-map
    default does not overwrite it.
    """
    # user pruned the finalize steps to a single-element list
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': ['default:commit-push']}}},
    )

    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # list preserved verbatim (atomic — not merged against the keyed-map default)
    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['plan']['phase-6-finalize']['steps'] == ['default:commit-push']
    assert 'plan.phase-6-finalize.steps' not in result['added']


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
