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
    # Arrange / Act
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert
    assert result['status'] == 'error'
    assert 'marshal.json' in result['error'].lower()


def test_sync_defaults_empty_marshal_gains_all_defaults(plan_context):
    """An empty marshal.json gains every key present in get_default_config()."""
    # Arrange
    _write_marshal(plan_context.fixture_dir, {})

    # Act
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert
    assert result['status'] == 'success'
    assert result['added_count'] > 0
    config = _read_marshal(plan_context.fixture_dir)
    assert config['plan']['phase-6-finalize']['auto_rebase_threshold'] == 'no_overlap_only'
    assert config['project']['default_base_branch'] == 'main'
    # Top-level default keys are added
    assert 'plan' in result['added']
    assert 'project' in result['added']


def test_sync_defaults_preserves_user_set_keys(plan_context):
    """A user-set scalar survives the sync; missing siblings are added."""
    # Arrange — user pinned pr_merge_strategy to a non-default value
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'pr_merge_strategy': 'merge'}}},
    )

    # Act
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert
    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    finalize = config['plan']['phase-6-finalize']
    # User override preserved (default would be 'squash')
    assert finalize['pr_merge_strategy'] == 'merge'
    # Missing sibling added
    assert finalize['auto_rebase_threshold'] == 'no_overlap_only'
    # The preserved key is NOT reported as added
    assert 'plan.phase-6-finalize.pr_merge_strategy' not in result['added']


def test_sync_defaults_preserves_user_set_false(plan_context):
    """A user-set False survives even when the default value is also False."""
    # Arrange — user explicitly disabled auto_merge_after_ci (matches default False)
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'auto_merge_after_ci': False}}},
    )

    # Act
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert — present means "key exists"; no value comparison, no re-add
    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['plan']['phase-6-finalize']['auto_merge_after_ci'] is False
    assert 'plan.phase-6-finalize.auto_merge_after_ci' not in result['added']


def test_sync_defaults_adds_deeply_nested_missing_key(plan_context):
    """A missing nested sub-key is added when its parent dict already exists."""
    # Arrange — phase-6-finalize exists but lacks auto_rebase_threshold
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'max_iterations': 3}}},
    )

    # Act
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert
    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    finalize = config['plan']['phase-6-finalize']
    assert finalize['max_iterations'] == 3
    assert finalize['auto_rebase_threshold'] == 'no_overlap_only'
    assert 'plan.phase-6-finalize.auto_rebase_threshold' in result['added']


def test_sync_defaults_lists_are_atomic(plan_context):
    """A user's list value is kept verbatim even when the default list differs."""
    # Arrange — user pruned the finalize steps list to a single step
    _write_marshal(
        plan_context.fixture_dir,
        {'plan': {'phase-6-finalize': {'steps': ['default:commit-push']}}},
    )

    # Act
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert — list preserved verbatim (not merged element-wise)
    assert result['status'] == 'success'
    config = _read_marshal(plan_context.fixture_dir)
    assert config['plan']['phase-6-finalize']['steps'] == ['default:commit-push']
    assert 'plan.phase-6-finalize.steps' not in result['added']


def test_sync_defaults_is_idempotent(plan_context):
    """Re-running sync-defaults immediately produces an empty added list."""
    # Arrange
    _write_marshal(plan_context.fixture_dir, {})
    first = cmd_sync_defaults(Namespace(audit_plan_id=None))
    assert first['status'] == 'success'
    assert first['added_count'] > 0

    # Act — second run
    second = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert
    assert second['status'] == 'success'
    assert second['added'] == []
    assert second['added_count'] == 0


def test_sync_defaults_reports_added_paths_sorted(plan_context):
    """The TOON report enumerates added dotted paths in sorted order."""
    # Arrange
    _write_marshal(plan_context.fixture_dir, {})

    # Act
    result = cmd_sync_defaults(Namespace(audit_plan_id=None))

    # Assert
    assert result['status'] == 'success'
    assert result['added'] == sorted(result['added'])
    assert result['added_count'] == len(result['added'])
