#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for lifecycle commands in manage-status.py script.

Tier 2 (direct import) tests with 3 subprocess tests for CLI plumbing.
"""

import argparse
import copy
import json
from typing import Any

from conftest import get_script_path, load_script_module, parse_ns, run_script

_BUNDLE = 'plan-marshall'
_SKILL = 'manage-status'
_SCRIPT = 'manage-status.py'

# Script path for remaining subprocess (CLI plumbing) tests
SCRIPT_PATH = get_script_path(_BUNDLE, _SKILL, _SCRIPT)


_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lc_cmd_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_lc_cmd_query')
_routing = load_script_module('plan-marshall', 'manage-status', '_cmd_routing.py', '_lc_cmd_routing')

cmd_archive, cmd_transition = _lifecycle.cmd_archive, _lifecycle.cmd_transition
cmd_list = _query.cmd_list
cmd_get_routing_context, cmd_route, cmd_self_test = (
    _routing.cmd_get_routing_context,
    _routing.cmd_route,
    _routing.cmd_self_test,
)

# Import toon_parser - conftest sets up PYTHONPATH
from toon_parser import parse_toon  # noqa: E402


def _verb_args(*argv: str) -> argparse.Namespace:
    """The namespace ``manage-status.py``'s OWN parser yields for ``argv``.

    ``register=False`` so building one never publishes ``manage-status`` in
    ``sys.modules`` beside the handler modules loaded above under their own
    explicit names.
    """
    args: argparse.Namespace = parse_ns(_BUNDLE, _SKILL, _SCRIPT, *argv, register=False)
    return args


def _variant(base: argparse.Namespace, **overrides: Any) -> argparse.Namespace:
    """Derive a namespace from a hoisted parser-derived base.

    The base supplies every parser default; ``overrides`` names only the fields
    this call differs in. A shallow copy is enough because the values are the
    parser's own scalars, and the base must stay unmutated for the other callers
    sharing it.
    """
    derived = copy.copy(base)
    for field, value in overrides.items():
        setattr(derived, field, value)
    return derived


#: One parser-derived namespace per lifecycle verb, hoisted to module scope
#: because ``parse_ns`` re-executes the script module on every call. Each carries
#: the ``command`` discriminator and the verb's real flag defaults — ``archive``'s
#: ``--reason`` was absent from the hand-built namespace entirely, and ``list``'s
#: ``--filter`` default now comes from the parser rather than a ``None`` repeated
#: at each call site.
_LIST_ARGS = _verb_args('list')
_ROUTE_ARGS = _verb_args('route', '--phase', '1-init')
_TRANSITION_ARGS = _verb_args('transition', '--plan-id', 'placeholder', '--completed', '1-init')
_ROUTING_CONTEXT_ARGS = _verb_args('get-routing-context', '--plan-id', 'placeholder')
_ARCHIVE_ARGS = _verb_args('archive', '--plan-id', 'placeholder')

# =============================================================================
# Helper: create a status.json with standard phase structure
# =============================================================================


def _create_status(ctx, plan_id='test-plan', current_phase='1-init', phases=None, title='Test Plan'):
    """Create a status.json in the plan directory."""
    if phases is None:
        phases = [
            {'name': '1-init', 'status': 'done' if current_phase != '1-init' else 'in_progress'},
            {'name': '2-refine', 'status': 'in_progress' if current_phase == '2-refine' else 'pending'},
            {'name': '3-outline', 'status': 'in_progress' if current_phase == '3-outline' else 'pending'},
            {'name': '4-plan', 'status': 'in_progress' if current_phase == '4-plan' else 'pending'},
            {'name': '5-execute', 'status': 'in_progress' if current_phase == '5-execute' else 'pending'},
            {'name': '6-finalize', 'status': 'in_progress' if current_phase == '6-finalize' else 'pending'},
        ]
    status = {
        'title': title,
        'current_phase': current_phase,
        'phases': phases,
        'created': '2026-01-01T00:00:00Z',
        'updated': '2026-01-01T00:00:00Z',
    }
    status_file = ctx.plan_dir_for(plan_id) / 'status.json'
    status_file.write_text(json.dumps(status, indent=2))
    return status


# =============================================================================
# Test: list command (Tier 2 - direct import)
# =============================================================================


def test_list_empty_plans_dir(plan_context):
    """Test listing when no plans exist."""
    # Remove the auto-created plan dir so plans/ is empty
    import shutil

    shutil.rmtree(plan_context.plan_dir)

    result = cmd_list(_LIST_ARGS)
    assert result['status'] == 'success'
    assert result['total'] == 0


def test_list_no_plans_directory(plan_context):
    """Test listing when plans directory does not exist at all."""
    # Remove entire plans directory
    import shutil

    plans_dir = plan_context.plans_dir
    shutil.rmtree(plans_dir)

    result = cmd_list(_LIST_ARGS)
    assert result['status'] == 'success'
    assert result['total'] == 0


def test_list_with_plans(plan_context):
    """Test listing when plans exist with status.json."""
    _create_status(plan_context, plan_id='lifecycle-list-plans', current_phase='2-refine')

    result = cmd_list(_LIST_ARGS)
    assert result['status'] == 'success'
    assert result['total'] >= 1


def test_list_with_filter(plan_context):
    """Test listing with phase filter."""
    _create_status(plan_context, plan_id='lifecycle-list-filter', current_phase='3-outline')

    # Filter for matching phase
    result = cmd_list(_variant(_LIST_ARGS, filter='3-outline'))
    assert result['status'] == 'success'
    assert result['total'] >= 1

    # Filter for non-matching phase
    result = cmd_list(_variant(_LIST_ARGS, filter='5-execute'))
    assert result['status'] == 'success'
    assert result['total'] == 0


# =============================================================================
# Test: route command (Tier 2 - direct import)
# =============================================================================


def test_route_valid_phases():
    """Test route returns correct skill for each known phase."""
    expected = {
        '1-init': 'plan-init',
        '2-refine': 'request-refine',
        '3-outline': 'solution-outline',
        '4-plan': 'task-plan',
        '5-execute': 'plan-execute',
        '6-finalize': 'plan-finalize',
    }
    for phase, expected_skill in expected.items():
        result = cmd_route(_variant(_ROUTE_ARGS, phase=phase))
        assert result['status'] == 'success'
        assert result['skill'] == expected_skill, f'Phase {phase}: expected {expected_skill}, got {result["skill"]}'


def test_route_unknown_phase():
    """Test route fails for an unknown phase."""
    result = cmd_route(_variant(_ROUTE_ARGS, phase='unknown-phase'))
    assert result['status'] == 'error'


# =============================================================================
# Test: transition command (Tier 2 - direct import)
# =============================================================================


def test_transition_valid(plan_context):
    """Test transitioning from one phase to the next."""
    _create_status(plan_context, plan_id='lifecycle-trans', current_phase='1-init')

    result = cmd_transition(_variant(_TRANSITION_ARGS, plan_id='lifecycle-trans'))
    assert result['status'] == 'success'
    assert result['completed_phase'] == '1-init'
    assert result['next_phase'] == '2-refine'


def test_transition_last_phase(plan_context):
    """Test transitioning the final phase marks all completed."""
    phases = [
        {'name': '1-init', 'status': 'done'},
        {'name': '2-refine', 'status': 'done'},
        {'name': '3-outline', 'status': 'done'},
        {'name': '4-plan', 'status': 'done'},
        {'name': '5-execute', 'status': 'done'},
        {'name': '6-finalize', 'status': 'in_progress'},
    ]
    _create_status(plan_context, plan_id='lifecycle-trans-last', current_phase='6-finalize', phases=phases)

    result = cmd_transition(
        _variant(_TRANSITION_ARGS, plan_id='lifecycle-trans-last', completed='6-finalize')
    )
    assert result['status'] == 'success'
    assert result['message'] == 'All phases completed'


def test_transition_invalid_phase(plan_context):
    """Test transition fails for a phase not in the plan."""
    _create_status(plan_context, plan_id='lifecycle-trans-badphase')

    result = cmd_transition(
        _variant(_TRANSITION_ARGS, plan_id='lifecycle-trans-badphase', completed='nonexistent-phase')
    )
    assert result['status'] == 'error'


def test_transition_nonexistent_plan(plan_context):
    """Test transition returns None for a plan without status.json."""
    result = cmd_transition(_variant(_TRANSITION_ARGS, plan_id='lifecycle-trans-noplan'))
    assert result is None


# =============================================================================
# Test: get-routing-context command (Tier 2 - direct import)
# =============================================================================


def test_get_routing_context_valid(plan_context):
    """Test getting routing context for a valid plan."""
    _create_status(plan_context, plan_id='lifecycle-ctx', current_phase='3-outline', title='My Feature')

    result = cmd_get_routing_context(_variant(_ROUTING_CONTEXT_ARGS, plan_id='lifecycle-ctx'))
    assert result['status'] == 'success'
    assert result['current_phase'] == '3-outline'
    assert result['skill'] == 'solution-outline'
    assert result['title'] == 'My Feature'


def test_get_routing_context_missing_plan(plan_context):
    """Test get-routing-context returns None for nonexistent plan."""
    result = cmd_get_routing_context(_variant(_ROUTING_CONTEXT_ARGS, plan_id='lifecycle-ctx-missing'))
    assert result is None


# =============================================================================
# Test: archive command (Tier 2 - direct import)
# =============================================================================


def test_archive_dry_run(plan_context):
    """Test archive with --dry-run shows what would happen."""
    _create_status(plan_context, plan_id='lifecycle-archive-dry')

    result = cmd_archive(_variant(_ARCHIVE_ARGS, plan_id='lifecycle-archive-dry', dry_run=True))
    assert result['status'] == 'success'
    # Plan directory should still exist after dry run
    assert plan_context.plan_dir_for('lifecycle-archive-dry').exists(), 'Plan dir should still exist after dry run'


def test_archive_actual(plan_context):
    """Test actual archive moves plan directory."""
    _create_status(plan_context, plan_id='lifecycle-archive-real')

    result = cmd_archive(_variant(_ARCHIVE_ARGS, plan_id='lifecycle-archive-real'))
    assert result['status'] == 'success'
    assert 'archived_to' in result
    # Plan directory should no longer exist
    assert not (plan_context.plans_dir / 'lifecycle-archive-real').exists(), 'Plan dir should be moved after archive'


def test_archive_nonexistent_plan(plan_context):
    """Test archive fails for nonexistent plan directory."""
    result = cmd_archive(_variant(_ARCHIVE_ARGS, plan_id='lifecycle-archive-nope'))
    assert result['status'] == 'error'


# =============================================================================
# Subprocess (CLI plumbing) tests
# =============================================================================


def test_cli_transition_invalid_plan_id():
    """Test transition CLI rejects invalid plan ID with exit code 1."""
    result = run_script(
        SCRIPT_PATH,
        'transition',
        '--plan-id',
        'INVALID ID!',
        '--completed',
        '1-init',
    )
    assert result.success, 'Expected exit 0 with TOON error for invalid plan ID'
    assert 'status: error' in result.stdout


def test_cli_archive_invalid_plan_id():
    """Test archive CLI rejects invalid plan ID with TOON error (exit 0)."""
    result = run_script(
        SCRIPT_PATH,
        'archive',
        '--plan-id',
        'BAD ID!',
    )
    assert result.success, 'Expected exit 0 with TOON error for invalid plan ID'
    assert 'status: error' in result.stdout


def test_cli_self_test_passes(plan_context):
    """Test self-test CLI reports all checks passing."""
    result = run_script(SCRIPT_PATH, 'self-test')
    assert result.success, f'Self-test failed: {result.stderr}'
    data = parse_toon(result.stdout)
    assert data['status'] == 'success'
    assert data['passed'] == 4
    assert data['failed'] == 0
    assert 'failures' not in data
