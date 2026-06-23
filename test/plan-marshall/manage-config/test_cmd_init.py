#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for init command in manage-config.

Tests init command variants including force overwrite and error handling.

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from test_helpers import SCRIPT_PATH, create_marshal_json

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_init_mod = _load_module('_cmd_init', '_cmd_init.py')

cmd_init = _cmd_init_mod.cmd_init

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402, I001


# `plan.phase-6-finalize.steps` and `plan.phase-5-execute.verification_steps`
# serialize on disk as the canonical keyed map: an id-keyed object
# `{step_id: {params}}` (`{}` for a config-less step) whose key insertion order
# is the execution order. This helper extracts the ordered id list from that
# keyed map.


def _step_ids(steps_map: dict) -> list:
    """Return the ordered step-id list from a keyed-map steps object."""
    return list(steps_map.keys())

# =============================================================================
# Init Command Tests (Tier 2 - direct import)
# =============================================================================


def test_init_creates_marshal_json(plan_context):
    """Test init creates marshal.json with defaults."""
    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    assert marshal_path.exists(), 'marshal.json should be created'

    config = json.loads(marshal_path.read_text())
    assert 'skill_domains' in config, 'Should have skill_domains'
    assert 'system' in config, 'Should have system'
    assert 'plan' in config, 'Should have plan'


def test_init_fails_if_exists(plan_context):
    """Test init fails if marshal.json already exists."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'error'
    assert 'already exists' in result['error'].lower()


def test_init_force_overwrites(plan_context):
    """Test init --force overwrites existing marshal.json."""
    # Create existing with custom content
    create_marshal_json(plan_context.fixture_dir, {'custom': True})

    result = cmd_init(Namespace(force=True))

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    assert 'skill_domains' in config, 'Should have default content'
    assert 'custom' not in config, 'Should not have old custom content'


def test_init_creates_parent_directory(plan_context):
    """Test init creates .plan directory if missing."""
    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'success'
    assert (plan_context.fixture_dir / 'marshal.json').exists()


def test_init_preserves_system_domain(plan_context):
    """Test init includes system domain in defaults."""
    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    assert 'system' in config.get('skill_domains', {}), 'Should include system domain'


def test_init_no_build_systems_key(plan_context):
    """Test init does NOT create build_systems key in marshal.json.

    Build systems are determined at runtime via extension discovery,
    not persisted in marshal.json.
    """
    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    assert 'build_systems' not in config, 'marshal.json should NOT contain build_systems key'


def test_init_no_extension_defaults_key(plan_context):
    """Test init does NOT create extension_defaults key in marshal.json.

    extension_defaults is auto-created on first access by get_extension_defaults(),
    so it does not need to be in the init defaults.
    """
    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    assert 'extension_defaults' not in config, 'marshal.json should NOT contain extension_defaults key'


def test_init_key_ordering(plan_context):
    """Test init creates marshal.json with correct key order.

    Canonical order: plan, skill_domains, system
    """
    result = cmd_init(Namespace(force=False))

    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())

    # Get actual key order from JSON
    actual_keys = list(config.keys())

    # Expected canonical order (alphabetical)
    expected_order = ['plan', 'skill_domains', 'system']

    # Filter to only keys that exist
    actual_order = [k for k in actual_keys if k in expected_order]
    expected_filtered = [k for k in expected_order if k in actual_keys]

    assert actual_order == expected_filtered, f'Key order should be {expected_filtered}, got {actual_order}'


def test_init_includes_verification_in_phase_5_execute(plan_context):
    """Test init creates marshal.json with verification config in phase-5-execute."""
    result = cmd_init(Namespace(force=False))
    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    plan = config.get('plan', {})
    assert 'phase-6-verify' not in plan, 'Should NOT have plan.phase-6-verify section'
    execute = plan['phase-5-execute']
    assert execute['max_iterations'] == 5
    # verification_steps is the canonical keyed-map form; key insertion order is
    # the execution order. Verify steps own no params, so each config-less step
    # maps to an empty {} param object.
    assert isinstance(execute['verification_steps'], dict)
    assert _step_ids(execute['verification_steps']) == [
        'default:verify:quality-gate',
        'default:verify:module-tests',
        'default:verify:coverage',
    ]
    assert all(params == {} for params in execute['verification_steps'].values())


def test_init_includes_phase_6_finalize(plan_context):
    """Test init creates marshal.json with plan.phase-6-finalize section."""
    result = cmd_init(Namespace(force=False))
    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    plan = config.get('plan', {})
    assert 'phase-6-finalize' in plan, 'Should have plan.phase-6-finalize section'
    finalize = plan['phase-6-finalize']
    assert finalize['max_iterations'] == 3
    assert 'steps' in finalize, 'Should have steps map'
    # steps is the canonical keyed-map form; membership checks operate on the
    # ordered step-id list extracted from the keyed map's keys.
    assert isinstance(finalize['steps'], dict)
    step_ids = _step_ids(finalize['steps'])
    assert 'default:commit-push' in step_ids
    assert 'default:record-metrics' in step_ids
    assert 'default:archive-plan' in step_ids
    # Ordering invariant: archive-plan must be the final finalize step (it moves the
    # plan directory, so nothing may run after it), and record-metrics must precede it
    # so metrics.md is written before the directory moves. The optional
    # print-phase-breakdown summary step legitimately runs between them — it reads
    # metrics.md and writes into the plan dir before archive captures it. Array
    # order is the execution order.
    record_idx = step_ids.index('default:record-metrics')
    archive_idx = step_ids.index('default:archive-plan')
    assert archive_idx == len(step_ids) - 1, 'default:archive-plan must be the final finalize step'
    assert record_idx < archive_idx, 'default:record-metrics must precede default:archive-plan'
    assert '1_commit_push' not in finalize, 'Old boolean keys should not exist'


def test_init_includes_phase_1_init(plan_context):
    """Test init creates marshal.json with plan.phase-1-init section."""
    result = cmd_init(Namespace(force=False))
    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    plan = config.get('plan', {})
    assert 'phase-1-init' in plan, 'Should have plan.phase-1-init section'
    assert plan['phase-1-init']['branch_strategy'] == 'feature'


def test_init_no_top_level_verification(plan_context):
    """Test init does NOT create top-level verification key."""
    result = cmd_init(Namespace(force=False))
    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    assert 'verification' not in config, 'Should NOT have top-level verification key'


def test_init_no_top_level_finalize(plan_context):
    """Test init does NOT create top-level finalize key."""
    result = cmd_init(Namespace(force=False))
    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    assert 'finalize' not in config, 'Should NOT have top-level finalize key'


def test_init_no_plan_defaults(plan_context):
    """Test init does NOT create plan.defaults key."""
    result = cmd_init(Namespace(force=False))
    assert result['status'] == 'success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text())
    plan = config.get('plan', {})
    assert 'defaults' not in plan, 'Should NOT have plan.defaults key'


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_init_creates_marshal_json(plan_context):
    """Test CLI plumbing: init creates marshal.json with TOON output."""
    result = run_script(SCRIPT_PATH, 'init')

    assert result.success, f'Init should succeed: {result.stderr}'
    assert 'success' in result.stdout.lower(), 'Should output success'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    assert marshal_path.exists(), 'marshal.json should be created'


def test_cli_init_force_overwrites(plan_context):
    """Test CLI plumbing: init --force overwrites existing."""
    create_marshal_json(plan_context.fixture_dir, {'custom': True})

    result = run_script(SCRIPT_PATH, 'init', '--force')

    assert result.success, f'Init --force should succeed: {result.stderr}'


# =============================================================================
# Main
# =============================================================================
