#!/usr/bin/env python3
"""Tests for phase-based plan commands in manage-config.

Tests plan phase-5-execute (including verification pipeline), phase-6-finalize pipeline commands,
as well as scalar phase commands (phase-1-init, phase-2-refine).

Tier 2 (direct import) tests with 2 subprocess tests for CLI plumbing.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch

from _layout_sim import build_phase_layout
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


# Load dependency modules first so sys.modules is populated with test-controlled instances
# before _cmd_quality_phases executes its module-level imports. This ensures patch.object
# calls in tests (e.g. patching _cmd_skill_domains.BUNDLES_DIR) affect the same objects
# that _cmd_quality_phases holds references to.
# _cmd_quality_phases must still be registered in sys.modules BEFORE _cmd_system_plan
# does `from _cmd_quality_phases import cmd_phase` — preserving that ordering.
_cmd_skill_domains = _load_module('_cmd_skill_domains', '_cmd_skill_domains.py')
_cmd_skill_resolution = _load_module('_cmd_skill_resolution', '_cmd_skill_resolution.py')
_config_defaults = _load_module('_config_defaults', '_config_defaults.py')
_cmd_quality_phases = _load_module('_cmd_quality_phases', '_cmd_quality_phases.py')
_cmd_system_plan = _load_module('_cmd_system_plan', '_cmd_system_plan.py')

cmd_plan = _cmd_system_plan.cmd_plan

# Import shared infrastructure (conftest.py sets up PYTHONPATH)
from conftest import run_script  # noqa: E402, I001


# `plan.phase-6-finalize.steps` and `plan.phase-5-execute.verification_steps`
# serialize on disk as the canonical keyed map: an id-keyed object
# `{step_id: {params}}` (`{}` for a config-less step) whose key insertion order
# is the execution order. These helpers extract the ordered id list and a single
# step's nested param object from that keyed map.


def _step_ids(steps_map: dict) -> list:
    """Return the ordered step-id list from a keyed-map steps object."""
    return list(steps_map.keys())


def _params_for(steps_map: dict, step_id: str):
    """Return a step's params from a keyed-map steps object.

    Returns the step's nested param object (``{}`` for a config-less step).
    Raises ``KeyError`` when the step id is absent.
    """
    return steps_map[step_id]

# =============================================================================
# phase-5-execute Verification Pipeline Command Tests (Tier 2)
# =============================================================================


def test_execute_verify_get(plan_context):
    """Test plan phase-5-execute get returns verification_steps list config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'max_iterations' in result
    assert 'verification_steps' in result
    assert 'default:verify:quality-gate' in result['verification_steps']


def test_execute_verify_set_max_iterations(plan_context):
    """Test plan phase-5-execute set-max-iterations for verification."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='set-max-iterations', value=10))

    assert result['status'] == 'success'

    # Verify changed
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-5-execute']['max_iterations'] == 10


def test_execute_set_steps_single_canonical_verify_round_trips(plan_context):
    """set-steps with a single canonical-verify step persists it to verification_steps.

    Every built-in canonical-verify step (`default:verify:{canonical}`) shares the
    single backing standards doc `canonical_verify.md` (order 10), so a single-step
    set-steps resolves its order cleanly and round-trips.
    """
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set-steps',
            steps='default:verify:quality-gate',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    # verification_steps persists as the canonical keyed map; a config-less step
    # maps to an empty {} param object.
    assert config['plan']['phase-5-execute']['verification_steps'] == {
        'default:verify:quality-gate': {}
    }


def test_execute_set_steps_multiple_canonical_verify_succeeds_ordered_by_list_position(plan_context):
    """set-steps over >1 canonical-verify step SUCCEEDS, ordered by list position.

    The built-in canonical-verify steps all resolve their order from the single
    `canonical_verify.md` doc (order 10), so they share a base order by design.
    They are EXEMPT from the distinct-order collision guard in
    `_resolve_step_orders` — multiple canonical-verify steps are valid, and their
    effective ordering comes from their position in the persisted
    `verification_steps` list (canonical_verify.md § "Ordering among
    canonical-verify entries"; data-model.md). This asserts the resolved contract:
    no order_collision, and list position is preserved verbatim.
    """
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set-steps',
            steps='default:verify:quality-gate,default:verify:module-tests',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    # Array order is the execution order — list position is preserved.
    assert _step_ids(config['plan']['phase-5-execute']['verification_steps']) == [
        'default:verify:quality-gate',
        'default:verify:module-tests',
    ]


def test_execute_set_steps_multiple_canonical_verify_preserves_reverse_list_order(plan_context):
    """Canonical-verify list position is the effective order — reversed input round-trips reversed.

    Because all canonical-verify steps share base order 10, the persisted order is
    determined ONLY by input list position (via the list-index offset in
    `_resolve_step_orders`). A reversed input list therefore persists reversed,
    proving the ordering is list-position-driven rather than collapsing to a
    discovery-order canonicalization.
    """
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set-steps',
            steps='default:verify:coverage,default:verify:module-tests,default:verify:quality-gate',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert _step_ids(config['plan']['phase-5-execute']['verification_steps']) == [
        'default:verify:coverage',
        'default:verify:module-tests',
        'default:verify:quality-gate',
    ]


def test_execute_add_step(plan_context, monkeypatch):
    """Test plan phase-5-execute add-step inserts an extension step at its discovered-order position."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject an extension step with a known discovery order — overrides no longer exist.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:verify:quality-gate', 'order': 10},
            {'name': 'default:verify:module-tests', 'order': 20},
            {'name': 'default:verify:coverage', 'order': 30},
            {'name': 'pm-documents:doc-verify', 'order': 500},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='pm-documents:doc-verify',
            position=None,
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    step_ids = _step_ids(config['plan']['phase-5-execute']['verification_steps'])
    assert 'pm-documents:doc-verify' in step_ids
    # Order 500 places it after the default built-ins (10, 20, 30) — last entry.
    assert step_ids[-1] == 'pm-documents:doc-verify'


def test_execute_remove_step(plan_context):
    """Test plan phase-5-execute remove-step removes from verification_steps list."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='remove-step',
            step='default:verify:quality-gate',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-5-execute']['verification_steps']
    assert 'default:verify:quality-gate' not in steps
    assert 'default:verify:module-tests' in steps


def test_execute_verify_get_field(plan_context):
    """Test plan phase-5-execute get --field returns specific verification field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='get',
            field='max_iterations',
        )
    )

    assert result['status'] == 'success'
    assert result['value'] == 5


def test_execute_add_step_duplicate(plan_context):
    """Test plan phase-5-execute add-step with existing step returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='default:verify:quality-gate',
            position=None,
        )
    )

    assert result['status'] == 'error'
    assert 'default:verify:quality-gate' in result['error']


def test_execute_remove_step_not_found(plan_context):
    """Test plan phase-5-execute remove-step with missing step returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='remove-step',
            step='nonexistent',
        )
    )

    assert result['status'] == 'error'
    assert 'nonexistent' in result['error']


# =============================================================================
# phase-6-finalize Command Tests (Tier 2)
# =============================================================================


def test_finalize_get(plan_context):
    """Test plan phase-6-finalize get returns steps list config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'max_iterations' in result
    assert 'steps' in result
    assert 'default:push' in result['steps']


def test_finalize_set_steps(plan_context):
    """Test plan phase-6-finalize set-steps replaces entire steps list."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:push,default:create-pr,default:archive-plan',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-6-finalize']['steps']
    assert _step_ids(steps) == ['default:push', 'default:create-pr', 'default:archive-plan']


def test_finalize_set_steps_empty_error(plan_context):
    """Test plan phase-6-finalize set-steps with empty list returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='set-steps', steps=''))

    assert result['status'] == 'error'


def test_finalize_add_step(plan_context, monkeypatch):
    """Test plan phase-6-finalize add-step places an extension step at its discovered-order position."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject discovery orders for the existing built-ins plus an extension step at order 75.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:push', 'order': 10},
            {'name': 'default:create-pr', 'order': 20},
            {'name': 'default:automated-review', 'order': 30},
            {'name': 'default:sonar-roundtrip', 'order': 40},
            {'name': 'default:lessons-capture', 'order': 50},
            {'name': 'default:branch-cleanup', 'order': 70},
            {'name': 'pm-dev-java:java-post-pr', 'order': 75},
            {'name': 'default:record-metrics', 'order': 990},
            {'name': 'default:archive-plan', 'order': 1000},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='pm-dev-java:java-post-pr',
            position=None,
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    step_ids = _step_ids(config['plan']['phase-6-finalize']['steps'])
    assert 'pm-dev-java:java-post-pr' in step_ids
    # Order 75 sits between branch-cleanup (70) and record-metrics (990)
    idx = step_ids.index('pm-dev-java:java-post-pr')
    assert step_ids[idx - 1] == 'default:branch-cleanup'
    assert step_ids[idx + 1] == 'default:record-metrics'


def test_finalize_add_step_sorts_by_order(plan_context, monkeypatch):
    """Test plan phase-6-finalize add-step places the step by discovered order (positional arg ignored)."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject a project step at order=1 so it sorts ahead of every built-in.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'project:finalize-step-custom', 'order': 1},
            {'name': 'default:push', 'order': 10},
            {'name': 'default:create-pr', 'order': 20},
            {'name': 'default:automated-review', 'order': 30},
            {'name': 'default:sonar-roundtrip', 'order': 40},
            {'name': 'default:lessons-capture', 'order': 50},
            {'name': 'default:branch-cleanup', 'order': 70},
            {'name': 'default:record-metrics', 'order': 990},
            {'name': 'default:archive-plan', 'order': 1000},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='project:finalize-step-custom',
            position=5,  # Ignored — sort by discovered order.
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-6-finalize']['steps']
    # Order 1 is lowest — custom step lands at the first list position.
    assert _step_ids(steps)[0] == 'project:finalize-step-custom'


def test_finalize_add_step_duplicate_error(plan_context):
    """Test plan phase-6-finalize add-step with duplicate returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='add-step',
            step='default:push',
            position=None,
        )
    )

    assert result['status'] == 'error'


def test_finalize_remove_step(plan_context):
    """Test plan phase-6-finalize remove-step removes a step."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='remove-step',
            step='default:sonar-roundtrip',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps = config['plan']['phase-6-finalize']['steps']
    assert 'default:sonar-roundtrip' not in steps


def test_finalize_remove_step_not_found_error(plan_context):
    """Test plan phase-6-finalize remove-step with missing step returns error."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='remove-step',
            step='bogus',
        )
    )

    assert result['status'] == 'error'


def test_finalize_set_max_iterations(plan_context):
    """Test plan phase-6-finalize set-max-iterations."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='set-max-iterations', value=7))

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-6-finalize']['max_iterations'] == 7


# =============================================================================
# Order-driven set-steps / add-step / overrides Tests (deliverable 6)
# =============================================================================


def test_finalize_set_steps_sorts_by_order(plan_context):
    """set-steps persists the steps list sorted by ascending resolved order."""
    create_marshal_json(plan_context.fixture_dir)

    # Pass built-in steps in reverse order to prove sorting.
    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:archive-plan,default:record-metrics,default:push,default:create-pr',
        )
    )

    assert result['status'] == 'success'
    # set-steps returns the keyed map; key insertion order is the execution order.
    assert list(result['steps'].keys()) == [
        'default:push',
        'default:create-pr',
        'default:record-metrics',
        'default:archive-plan',
    ]


def test_finalize_set_steps_missing_order_returns_error(plan_context):
    """set-steps fails with `error: missing_order` when a step has no resolvable order."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:push,pm-dev-java:java-post-pr',
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'missing_order'
    assert result['step'] == 'pm-dev-java:java-post-pr'
    assert result['phase'] == 'phase-6-finalize'


def test_finalize_set_steps_order_collision_returns_error(plan_context, monkeypatch):
    """set-steps fails with `error: order_collision` when two steps share the same discovered order."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject a discovery layout where push and create-pr collide at order 20.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:push', 'order': 20},
            {'name': 'default:create-pr', 'order': 20},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:push,default:create-pr',
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'order_collision'
    assert result['order'] == 20
    assert sorted(result['steps']) == ['default:create-pr', 'default:push']
    assert result['phase'] == 'phase-6-finalize'


def test_execute_add_step_order_collision_returns_error(plan_context, monkeypatch):
    """add-step fails with `error: order_collision` mirroring set-steps semantics."""
    create_marshal_json(plan_context.fixture_dir)

    # Inject discovery where the new extension step shares order 10 with the
    # quality-gate canonical-verify step.
    monkeypatch.setattr(
        _cmd_quality_phases,
        '_discover_steps_for_phase',
        lambda phase: [
            {'name': 'default:verify:quality-gate', 'order': 10},
            {'name': 'default:verify:module-tests', 'order': 20},
            {'name': 'default:verify:coverage', 'order': 30},
            {'name': 'pm-documents:doc-verify', 'order': 10},
        ],
    )

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='add-step',
            step='pm-documents:doc-verify',
            position=None,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'order_collision'
    assert result['order'] == 10


# =============================================================================
# Layout-aware set-steps round-trip (cache + source layouts)
# =============================================================================


def test_execute_set_steps_round_trip_cache_layout(plan_context):
    """A single canonical-verify step resolves its order from the versioned cache layout.

    The canonical-verify steps all resolve their order from the single
    `canonical_verify.md` doc; the layout sim writes that one doc for every
    `default:verify:{canonical}` step. This proves the order resolves (no
    missing_order) when discovery runs against the versioned plugin-cache shape.
    """
    create_marshal_json(plan_context.fixture_dir)
    cache_base = build_phase_layout(
        plan_context.fixture_dir / 'cache_bundles',
        'phase-5-execute',
        _config_defaults.BUILT_IN_VERIFY_STEPS,
        cache_layout=True,
    )

    with (
        patch.object(_cmd_skill_domains, 'BUNDLES_DIR', cache_base),
        patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=[]),
    ):
        result = cmd_plan(
            Namespace(
                sub_noun='phase-5-execute',
                verb='set-steps',
                steps='default:verify:quality-gate',
            )
        )

    assert result['status'] == 'success', f'Expected success (no missing_order) in cache layout, got {result}'
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    # config-less step persists as a {step_id: {}} entry in the keyed map
    assert config['plan']['phase-5-execute']['verification_steps'] == {
        'default:verify:quality-gate': {}
    }


def test_execute_set_steps_round_trip_source_layout(plan_context):
    """A single canonical-verify step resolves its order from the source layout.

    Mirrors the cache-layout round-trip against the marketplace-source shape;
    proves `canonical_verify.md`'s order resolves there too (no missing_order).
    """
    create_marshal_json(plan_context.fixture_dir)
    source_base = build_phase_layout(
        plan_context.fixture_dir / 'source_bundles',
        'phase-5-execute',
        _config_defaults.BUILT_IN_VERIFY_STEPS,
        cache_layout=False,
    )

    with (
        patch.object(_cmd_skill_domains, 'BUNDLES_DIR', source_base),
        patch.object(_cmd_skill_domains, 'discover_all_extensions', return_value=[]),
    ):
        result = cmd_plan(
            Namespace(
                sub_noun='phase-5-execute',
                verb='set-steps',
                steps='default:verify:quality-gate',
            )
        )

    assert result['status'] == 'success', f'Expected success (no missing_order) in source layout, got {result}'
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    # config-less step persists as a {step_id: {}} entry in the keyed map
    assert config['plan']['phase-5-execute']['verification_steps'] == {
        'default:verify:quality-gate': {}
    }


# =============================================================================
# Scalar Phase Command Tests (Tier 2)
# =============================================================================


def test_phase_1_init_get(plan_context):
    """Test plan phase-1-init get returns config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-1-init', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'branch_strategy' in result


def test_phase_1_init_set(plan_context):
    """Test plan phase-1-init set updates a field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-1-init',
            verb='set',
            field='branch_strategy',
            value='feature-branch',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-1-init']['branch_strategy'] == 'feature-branch'


def test_phase_2_refine_get(plan_context):
    """Test plan phase-2-refine get returns config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-2-refine', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'confidence_threshold' in result


def test_phase_2_refine_set(plan_context):
    """Test plan phase-2-refine set updates a field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-2-refine',
            verb='set',
            field='confidence_threshold',
            value='90',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-2-refine']['confidence_threshold'] == 90


def test_phase_5_execute_get(plan_context):
    """Test plan phase-5-execute get returns config."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-5-execute', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'commit_and_push' in result
    assert 'compatibility' not in result


def test_phase_5_execute_set(plan_context):
    """Test plan phase-5-execute set updates a field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='commit_and_push',
            value='true',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-5-execute']['commit_and_push'] is True


def test_phase_5_execute_get_per_deliverable_build_default(plan_context):
    """Test plan phase-5-execute get returns the per_deliverable_build list default."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(sub_noun='phase-5-execute', verb='get', field='per_deliverable_build')
    )

    assert result['status'] == 'success'
    # The knob is now a LIST of default:verify:{canonical} step IDs.
    assert result['value'] == ['default:verify:compile', 'default:verify:module-tests']


def test_phase_5_execute_set_per_deliverable_build_list_round_trips(plan_context):
    """Test plan phase-5-execute set parses the comma-separated value into a validated list."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='per_deliverable_build',
            value='default:verify:compile,default:verify:module-tests',
        )
    )

    assert result['status'] == 'success'
    # the comma-separated --value round-trips as a list on disk
    assert result['value'] == ['default:verify:compile', 'default:verify:module-tests']
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-5-execute']['per_deliverable_build'] == [
        'default:verify:compile',
        'default:verify:module-tests',
    ]


def test_phase_5_execute_set_per_deliverable_build_empty_disables(plan_context):
    """Test plan phase-5-execute set with an empty value persists [] (disables the focused build)."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='per_deliverable_build',
            value='',
        )
    )

    assert result['status'] == 'success'
    assert result['value'] == []
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-5-execute']['per_deliverable_build'] == []


def test_phase_6_finalize_set_steps_rejected_and_config_unchanged(plan_context):
    """`set --field steps` on phase-6-finalize is rejected without string-corrupting the keyed map."""
    create_marshal_json(plan_context.fixture_dir)
    before = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    before_steps = before['plan']['phase-6-finalize']['steps']

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set',
            field='steps',
            value='default:push',
        )
    )

    assert result['status'] == 'error'
    # Message names the keyed step-map and the correct alternative verbs.
    assert 'keyed step-map' in result['error']
    assert 'set-steps' in result['error']
    assert 'add-step' in result['error']
    assert 'remove-step' in result['error']
    assert 'step set' in result['error']
    # The on-disk keyed map is left exactly as seeded (no string corruption).
    after = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert after['plan']['phase-6-finalize']['steps'] == before_steps
    assert isinstance(after['plan']['phase-6-finalize']['steps'], dict)


def test_phase_5_execute_set_verification_steps_rejected_and_config_unchanged(plan_context):
    """`set --field verification_steps` on phase-5-execute is rejected without corrupting the keyed map."""
    create_marshal_json(plan_context.fixture_dir)
    before = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    before_steps = before['plan']['phase-5-execute']['verification_steps']

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='verification_steps',
            value='default:verify:quality-gate',
        )
    )

    assert result['status'] == 'error'
    assert 'keyed step-map' in result['error']
    assert 'set-steps' in result['error']
    # The on-disk keyed map is unchanged.
    after = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert after['plan']['phase-5-execute']['verification_steps'] == before_steps
    assert isinstance(after['plan']['phase-5-execute']['verification_steps'], dict)


def test_phase_5_execute_set_scalar_field_still_succeeds(plan_context):
    """The keyed-step-map guard must not over-reject a normal scalar `set --field`."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='commit_and_push',
            value='false',
        )
    )

    assert result['status'] == 'success'
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-5-execute']['commit_and_push'] is False


def test_phase_5_execute_set_per_deliverable_build_rejects_retired_enum(plan_context):
    """Test plan phase-5-execute set rejects the retired per_deliverable_build enum strings."""
    create_marshal_json(plan_context.fixture_dir)

    # the retired 'compile+scoped-test' enum value must be rejected with a migration error
    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='per_deliverable_build',
            value='compile+scoped-test',
        )
    )

    assert result['status'] == 'error'
    assert 'no longer accepts the enum value' in result['error']


def test_phase_5_execute_set_per_deliverable_build_rejects_non_canonical_entry(plan_context):
    """Test plan phase-5-execute set rejects a list entry lacking the default:verify: prefix."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='per_deliverable_build',
            value='default:verify:compile,bogus',
        )
    )

    assert result['status'] == 'error'
    assert 'every entry must be a' in result['error']


def test_phase_5_execute_remove_field_deletes_persisted_key(plan_context):
    """Test plan phase-5-execute remove-field deletes a persisted phase key.

    Removing per_deliverable_build (a defaults-seeded key) re-exposes the list
    default on the next get — the verb removes an explicit override only.
    """
    create_marshal_json(plan_context.fixture_dir)

    # set an explicit override so the key is present in the persisted section
    set_result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='set',
            field='per_deliverable_build',
            value='default:verify:compile',
        )
    )
    assert set_result['status'] == 'success'

    remove_result = cmd_plan(
        Namespace(sub_noun='phase-5-execute', verb='remove-field', field='per_deliverable_build')
    )

    assert remove_result['status'] == 'success'
    assert remove_result['removed'] is True

    # the seeded default is re-exposed after the override is removed
    get_result = cmd_plan(
        Namespace(sub_noun='phase-5-execute', verb='get', field='per_deliverable_build')
    )
    assert get_result['value'] == ['default:verify:compile', 'default:verify:module-tests']


def test_phase_5_execute_remove_field_errors_on_absent_key(plan_context):
    """Test plan phase-5-execute remove-field errors when the key is absent from the persisted section."""
    create_marshal_json(plan_context.fixture_dir)

    # the legacy `steps` key has no default and is absent from a fresh config
    result = cmd_plan(
        Namespace(sub_noun='phase-5-execute', verb='remove-field', field='steps')
    )

    assert result['status'] == 'error'


def test_phase_2_refine_get_includes_compatibility(plan_context):
    """Test plan phase-2-refine get returns compatibility."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(Namespace(sub_noun='phase-2-refine', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'compatibility' in result
    assert 'confidence_threshold' in result


def test_phase_2_refine_set_compatibility(plan_context):
    """Test plan phase-2-refine set updates compatibility field."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-2-refine',
            verb='set',
            field='compatibility',
            value='deprecation',
        )
    )

    assert result['status'] == 'success'

    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert config['plan']['phase-2-refine']['compatibility'] == 'deprecation'


# =============================================================================
# One-stop `step get` / `step set` verb (keyed-map step params)
# =============================================================================


def test_finalize_step_get_returns_complete_param_object(plan_context):
    """`step get --step-id default:automated-review` returns the full nested param object in one call."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:automated-review',
        )
    )

    assert result['status'] == 'success'
    assert result['step_id'] == 'default:automated-review'
    # the complete param object is returned in a single call
    assert result['params'] == {'review_bot_buffer_seconds': 300}


def test_finalize_step_get_returns_empty_params_for_ownerless_step(plan_context):
    """`step get` returns the empty param object for a step that owns no params."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:push',
        )
    )

    assert result['status'] == 'success'
    assert result['params'] == {}


def test_finalize_step_get_absent_step_id_errors(plan_context):
    """`step get` errors when the step id is absent from the keyed map."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:nonexistent',
        )
    )

    assert result['status'] == 'error'
    assert 'default:nonexistent' in result['error']


def test_finalize_step_set_writes_single_param_and_round_trips(plan_context):
    """`step set` writes one step-owned param into the step's nested object and round-trips via get."""
    create_marshal_json(plan_context.fixture_dir)

    set_result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='set',
            step_id='default:automated-review',
            param='review_bot_buffer_seconds',
            value='240',
        )
    )

    assert set_result['status'] == 'success'
    # value is coerced (string -> int)
    assert set_result['params']['review_bot_buffer_seconds'] == 240

    # round-trips through step get
    get_result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:automated-review',
        )
    )
    assert get_result['params']['review_bot_buffer_seconds'] == 240

    # persisted on disk inside the keyed-map step structure (nested param object)
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    persisted = _params_for(config['plan']['phase-6-finalize']['steps'], 'default:automated-review')
    assert persisted['review_bot_buffer_seconds'] == 240


def test_finalize_step_set_preserves_other_params(plan_context):
    """`step set` writing one param leaves the step's other params untouched."""
    create_marshal_json(plan_context.fixture_dir)

    # seed two params on the branch-cleanup step via two set calls
    cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='set',
            step_id='default:branch-cleanup',
            param='pr_merge_strategy',
            value='squash',
        )
    )
    cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='set',
            step_id='default:branch-cleanup',
            param='final_merge_without_asking',
            value='true',
        )
    )

    get_result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:branch-cleanup',
        )
    )

    assert get_result['status'] == 'success'
    assert get_result['params']['pr_merge_strategy'] == 'squash'
    assert get_result['params']['final_merge_without_asking'] is True


def test_finalize_step_set_absent_step_id_errors(plan_context):
    """`step set` errors when the step id is absent from the keyed map."""
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='set',
            step_id='default:nonexistent',
            param='pr_merge_strategy',
            value='merge',
        )
    )

    assert result['status'] == 'error'
    assert 'default:nonexistent' in result['error']


# =============================================================================
# Step-folded run-at-all / escape-hatch knobs (simplify / self_review /
# drop_review_on_scope_gate) live nested under their owning finalize step's param
# map; qgate stays a flat phase-level sibling.
# =============================================================================


def _marshal_without_finalize_section() -> dict:
    """A config whose plan.phase-6-finalize is absent → defaults supply the seed.

    The defaults-merge in `cmd_plan` brings the parser-resolved step-owned params
    (the finalize-step seed delegates to configurable_contract, including the
    folded `simplify` / `self_review` / `drop_review_on_scope_gate` knobs) into the
    resolved section, so the step-owned read path is exercised against the
    canonical default shape.
    """
    return {
        'skill_domains': {},
        'system': {'retention': {'logs_days': 1, 'archived_plans_days': 5, 'temp_on_maintenance': True}},
        'plan': {
            'phase-1-init': {'branch_strategy': 'direct'},
            'phase-2-refine': {'confidence_threshold': 95, 'compatibility': 'breaking'},
            'phase-3-outline': {},
            'phase-4-plan': {},
            'phase-5-execute': {},
        },
        'providers': [],
    }


def test_finalize_step_get_simplify_reads_from_owning_step_param_map(plan_context):
    """`simplify` is read from its owning step `default:finalize-step-simplify`.

    The knob folded out of its former flat-sibling location into the
    simplify-step's nested param object; the default is `auto`.
    """
    create_marshal_json(plan_context.fixture_dir, _marshal_without_finalize_section())

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='get',
            step_id='default:finalize-step-simplify',
        )
    )

    assert result['status'] == 'success'
    assert result['params']['simplify'] == 'auto'


def test_finalize_step_set_simplify_round_trips_under_owning_step(plan_context):
    """`step set` writes `simplify` into its owning step and round-trips on disk."""
    create_marshal_json(plan_context.fixture_dir, _marshal_without_finalize_section())

    set_result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='set',
            step_id='default:finalize-step-simplify',
            param='simplify',
            value='never',
        )
    )

    assert set_result['status'] == 'success'
    assert set_result['params']['simplify'] == 'never'

    # Persisted nested under the owning step's value in the keyed map.
    config = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    persisted = _params_for(config['plan']['phase-6-finalize']['steps'], 'default:finalize-step-simplify')
    assert persisted['simplify'] == 'never'


def test_finalize_get_no_longer_surfaces_folded_knobs_as_flat_siblings(plan_context):
    """`phase-6-finalize get` no longer carries the three folded knobs as flat fields.

    `simplify`, `self_review`, and `drop_review_on_scope_gate` moved out of the
    flat phase-level section into their owning step's nested param map. The flat
    `get` payload must not surface them. `qgate` remains a flat sibling.
    """
    create_marshal_json(plan_context.fixture_dir, _marshal_without_finalize_section())

    result = cmd_plan(Namespace(sub_noun='phase-6-finalize', verb='get', field=None))

    assert result['status'] == 'success'
    assert 'simplify' not in result
    assert 'self_review' not in result
    assert 'drop_review_on_scope_gate' not in result
    # qgate stays a flat phase-level sibling.
    assert result['qgate'] == 'auto'


def test_finalize_get_folded_knob_field_is_rejected(plan_context):
    """`phase-6-finalize get --field simplify` errors — the flat field is gone.

    The knob is no longer a flat phase-level field, so the scalar field read
    must report it as unknown rather than returning a stale flat value.
    """
    create_marshal_json(plan_context.fixture_dir, _marshal_without_finalize_section())

    result = cmd_plan(
        Namespace(sub_noun='phase-6-finalize', verb='get', field='simplify')
    )

    assert result['status'] == 'error'
    assert 'simplify' in result['error']


# =============================================================================
# READER tests: _steps_map normalizes the keyed-map on-disk form to the internal
# {step_id: {params}} dict.
# =============================================================================
#
# _steps_map is a pure normalizer over the value read from
# section[step_key]: it accepts the canonical keyed-map dict (or None), coerces
# each config-less value to {}, and returns a fresh ordered dict.


def test_steps_map_normalizes_config_less_and_param_bearing_values():
    """A keyed-map input (config-less {} + param-bearing object) normalizes correctly."""
    result = _cmd_quality_phases._steps_map(
        {
            'default:push': {},
            'default:automated-review': {'review_bot_buffer_seconds': 300},
        }
    )

    assert result == {
        'default:push': {},
        'default:automated-review': {'review_bot_buffer_seconds': 300},
    }


def test_steps_map_preserves_input_order():
    """Key insertion order is preserved as the internal dict's (execution) order."""
    result = _cmd_quality_phases._steps_map(
        {
            'default:archive-plan': {},
            'default:push': {},
            'default:create-pr': {},
        }
    )

    assert list(result.keys()) == [
        'default:archive-plan',
        'default:push',
        'default:create-pr',
    ]


def test_steps_map_empty_dict_yields_empty_dict():
    """An empty keyed map normalizes to an empty dict (edge case)."""
    assert _cmd_quality_phases._steps_map({}) == {}


def test_steps_map_single_entry_keyed_map():
    """Single-entry keyed maps — one config-less, one param-bearing (edge case)."""
    assert _cmd_quality_phases._steps_map({'default:push': {}}) == {
        'default:push': {}
    }
    assert _cmd_quality_phases._steps_map(
        {'default:automated-review': {'review_bot_buffer_seconds': 300}}
    ) == {'default:automated-review': {'review_bot_buffer_seconds': 300}}


def test_steps_map_null_value_coerces_to_empty():
    """A keyed-map value that is null/{} coerces to an empty param dict."""
    assert _cmd_quality_phases._steps_map({'default:push': None}) == {
        'default:push': {}
    }
    assert _cmd_quality_phases._steps_map({'default:push': {}}) == {
        'default:push': {}
    }


def test_steps_map_returns_fresh_dict_callers_can_mutate():
    """The normalizer returns a fresh dict so callers may mutate it safely."""
    raw = {'default:push': {}}
    result = _cmd_quality_phases._steps_map(raw)
    result['default:create-pr'] = {}

    # The source structure is untouched by the caller-side mutation.
    assert raw == {'default:push': {}}


# =============================================================================
# Keyed-map write round-trip (write verbs persist the keyed map)
# =============================================================================
#
# `create_marshal_json` seeds `verification_steps` / `steps` on disk in the
# canonical keyed-map form (a JSON object). The reader (`_steps_map`) normalizes
# that to the internal id-keyed map, and every config WRITE verb persists the
# keyed map directly. These tests assert the full read-modify-write cycle stays
# keyed-map-native: a write verb rewrites the keyed map (still a dict), and a
# second write verb is IDEMPOTENT (stays a keyed map).


def test_execute_remove_step_persists_keyed_map_form(plan_context):
    """A write verb against a keyed-map `verification_steps` rewrites it as a keyed map.

    The seeded fixture stores `verification_steps` as the keyed map (a dict).
    After `remove-step` the on-disk value is still the canonical keyed map (a
    JSON object), with the remaining config-less step mapping to {}.
    """
    create_marshal_json(plan_context.fixture_dir)

    # Precondition: the seed is the keyed map (dict) on disk.
    before = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert isinstance(before['plan']['phase-5-execute']['verification_steps'], dict)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-5-execute',
            verb='remove-step',
            step='default:verify:quality-gate',
        )
    )

    assert result['status'] == 'success'

    after = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    persisted = after['plan']['phase-5-execute']['verification_steps']
    # Persisted as the canonical keyed map (a dict, not a list).
    assert isinstance(persisted, dict)
    # The remaining config-less step maps to {} in the keyed map.
    assert persisted == {'default:verify:module-tests': {}}


def test_finalize_remove_step_persists_keyed_map_and_is_idempotent(plan_context):
    """Each write verb persists the keyed map; a second write stays a keyed map (idempotent).

    Round-trips the full read-modify-write cycle: the seed is the keyed map; the
    first `remove-step` rewrites it as a keyed map; reading that back and applying
    a second `remove-step` re-persists a keyed map again — the write path is
    idempotent over the keyed-map form.
    """
    create_marshal_json(plan_context.fixture_dir)

    # Precondition: keyed map (dict) on disk, with a param-bearing step.
    before = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert isinstance(before['plan']['phase-6-finalize']['steps'], dict)

    # First write — rewrites the keyed map.
    first = cmd_plan(
        Namespace(sub_noun='phase-6-finalize', verb='remove-step', step='default:lessons-capture')
    )
    assert first['status'] == 'success'

    after_first = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps_after_first = after_first['plan']['phase-6-finalize']['steps']
    assert isinstance(steps_after_first, dict)
    assert 'default:lessons-capture' not in _step_ids(steps_after_first)
    # The param-bearing step keeps its nested object in the keyed map.
    assert _params_for(steps_after_first, 'default:automated-review') == {
        'review_bot_buffer_seconds': 300
    }

    # Second write — operates on the keyed-map on-disk value; result is still a keyed map.
    second = cmd_plan(
        Namespace(sub_noun='phase-6-finalize', verb='remove-step', step='default:sonar-roundtrip')
    )
    assert second['status'] == 'success'

    after_second = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    steps_after_second = after_second['plan']['phase-6-finalize']['steps']
    # Idempotent over the keyed-map form — no shape regression on the second write.
    assert isinstance(steps_after_second, dict)
    assert 'default:sonar-roundtrip' not in _step_ids(steps_after_second)
    # The param-bearing step still survives with its nested object.
    assert _params_for(steps_after_second, 'default:automated-review') == {
        'review_bot_buffer_seconds': 300
    }


def test_step_set_against_keyed_map_persists_keyed_map_form(plan_context):
    """`step set` against a keyed-map `steps` persists the keyed map on disk.

    The param-writing verb reads the keyed map, mutates one step's nested params,
    and persists the keyed map directly. The on-disk value is the canonical keyed
    map, with the touched step carrying its nested param object.
    """
    create_marshal_json(plan_context.fixture_dir)

    # Precondition: keyed map (dict) on disk.
    before = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    assert isinstance(before['plan']['phase-6-finalize']['steps'], dict)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='step',
            step_verb='set',
            step_id='default:branch-cleanup',
            param='pr_merge_strategy',
            value='rebase',
        )
    )

    assert result['status'] == 'success'

    after = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    persisted = after['plan']['phase-6-finalize']['steps']
    # Persisted as the canonical keyed map on the param write.
    assert isinstance(persisted, dict)
    # The touched param-bearing step carries the override in its nested object.
    params = _params_for(persisted, 'default:branch-cleanup')
    assert params['pr_merge_strategy'] == 'rebase'
    # A config-less step persists as a {step_id: {}} entry.
    assert 'default:push' in _step_ids(persisted)
    assert _params_for(persisted, 'default:push') == {}


def test_set_steps_against_keyed_map_preserves_params(plan_context):
    """`set-steps` over a keyed map preserves existing per-step params.

    Reordering the steps via `set-steps` reads the keyed map, so the per-step
    params of retained steps survive into the rewritten keyed map rather than
    being dropped — the param-preservation contract over the keyed-map form.
    """
    create_marshal_json(plan_context.fixture_dir)

    result = cmd_plan(
        Namespace(
            sub_noun='phase-6-finalize',
            verb='set-steps',
            steps='default:automated-review,default:push,default:create-pr',
        )
    )

    assert result['status'] == 'success'

    after = json.loads((plan_context.fixture_dir / 'marshal.json').read_text())
    persisted = after['plan']['phase-6-finalize']['steps']
    assert isinstance(persisted, dict)
    # The retained param-bearing step keeps its params.
    assert _params_for(persisted, 'default:automated-review') == {
        'review_bot_buffer_seconds': 300
    }


# =============================================================================
# CLI Plumbing Tests (Tier 3 - subprocess)
# =============================================================================


def test_cli_plan_phase_5_execute_get(plan_context):
    """Test CLI plumbing: plan phase-5-execute get outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'plan', 'phase-5-execute', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'max_iterations' in result.stdout


def test_cli_plan_phase_6_finalize_get(plan_context):
    """Test CLI plumbing: plan phase-6-finalize get outputs TOON."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(SCRIPT_PATH, 'plan', 'phase-6-finalize', 'get')

    assert result.success, f'Should succeed: {result.stderr}'
    assert 'max_iterations' in result.stdout


def test_cli_set_step_order_override_no_longer_registered(plan_context):
    """Regression: the set-step-order-override verb is no longer a registered argparse choice."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH,
        'plan',
        'phase-6-finalize',
        'set-step-order-override',
        '--step',
        'foo',
        '--order',
        '1',
    )

    assert not result.success
    combined = (result.stderr + result.stdout).lower()
    assert 'invalid choice' in combined or 'unrecognized' in combined


def test_cli_remove_step_order_override_no_longer_registered(plan_context):
    """Regression: the remove-step-order-override verb is no longer a registered argparse choice."""
    create_marshal_json(plan_context.fixture_dir)

    result = run_script(
        SCRIPT_PATH,
        'plan',
        'phase-6-finalize',
        'remove-step-order-override',
        '--step',
        'foo',
    )

    assert not result.success
    combined = (result.stderr + result.stdout).lower()
    assert 'invalid choice' in combined or 'unrecognized' in combined


# =============================================================================
# Main
# =============================================================================
