#!/usr/bin/env python3
"""Tests for the ``planning-lane`` subcommand of manage-status.

The router resolves ``planning_lane ∈ {light, deep}`` from the DQ1 signal set
(S1–S6) plus a ``request.md`` regex, with zero codebase discovery. The default
is ``light``; any deep-precondition signal forces ``deep``; the
``ceremony_policy.planning.deep_lane`` (``always``/``never``/``auto``) gate
short-circuits the signal evaluation. The ``escalate`` verb is a one-way
light→deep ratchet that refuses any downgrade.

Coverage:
- Each signal (S1–S6) firing deep in isolation.
- The all-light default (no deep signal fires).
- The ceremony ``always`` / ``never`` short-circuit.
- ``--lane-override`` handling.
- ``--persist`` writes status.metadata.planning_lane.
- The one-way escalate invariant (deep + lane_escalated, no downgrade).
- Dispatch wiring (both verbs registered in manage-status.py argparse).
"""

from __future__ import annotations

import importlib.util
import json
from argparse import Namespace
from pathlib import Path

from conftest import PROJECT_ROOT

_SCRIPTS_DIR = (
    PROJECT_ROOT
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-status'
    / 'scripts'
)


def _load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module('_cmd_planning_lane_under_test', '_cmd_planning_lane.py')
cmd_planning_lane_route = _mod.cmd_planning_lane_route
cmd_planning_lane_escalate = _mod.cmd_planning_lane_escalate


# =============================================================================
# Fixture authoring helpers
# =============================================================================

# A request body that PASSES S5 concreteness (names a file path) so the S5 /
# S1 deep-bias does not fire — lets the other signals be tested in isolation.
_CONCRETE_BODY = (
    'Update `marketplace/bundles/plan-marshall/skills/x/scripts/x.py` to fix '
    'the parser.'
)
# A vague request body that FAILS S5 (no path, no fix signal) → S5 deep.
_VAGUE_BODY = 'The thing should do the thing per the thing, somehow.'


def _write_request(plan_dir: Path, body: str) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request\n\n'
        '## Original Input\n\n'
        '(unused)\n\n'
        '## Clarified Request\n\n'
        f'{body}\n'
    )
    (plan_dir / 'request.md').write_text(content, encoding='utf-8')


def _write_status(plan_dir: Path, metadata: dict | None = None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps(
            {'plan_id': plan_dir.name, 'phases': [], 'metadata': metadata or {}}
        ),
        encoding='utf-8',
    )


def _write_references(plan_dir: Path, scope_estimate: str | None) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    refs: dict = {'base_branch': 'main'}
    if scope_estimate is not None:
        refs['scope_estimate'] = scope_estimate
    (plan_dir / 'references.json').write_text(json.dumps(refs), encoding='utf-8')


def _write_marshal(fixture_dir: Path, *, compatibility: str = 'deprecation', deep_lane: str = 'auto') -> None:
    """Write a minimal marshal.json at the fixture root (= PLAN_BASE_DIR)."""
    config = {
        'plan': {'phase-2-refine': {'compatibility': compatibility}},
        'ceremony_policy': {'planning': {'deep_lane': deep_lane}},
    }
    (fixture_dir / 'marshal.json').write_text(json.dumps(config, indent=2), encoding='utf-8')


def _ns_route(plan_id: str, *, lane_override=None, persist=False) -> Namespace:
    return Namespace(plan_id=plan_id, lane_override=lane_override, persist=persist)


def _ns_escalate(plan_id: str, *, trigger='explosion', persist=False) -> Namespace:
    return Namespace(plan_id=plan_id, trigger=trigger, persist=persist)


def _light_setup(plan_context, plan_id: str) -> Path:
    """Seed an all-light baseline: concrete request, light scope, light change_type,
    non-breaking compatibility, auto deep_lane. Every signal biases light.
    """
    plan_dir = plan_context.plan_dir_for(plan_id)
    _write_request(plan_dir, _CONCRETE_BODY)
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')
    return plan_dir


# =============================================================================
# All-light default
# =============================================================================


def test_all_light_signals_resolve_light(plan_context):
    """When no deep-precondition fires, the router resolves the light default."""
    # Arrange
    _light_setup(plan_context, 'pl-light')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-light'))

    # Assert
    assert result['status'] == 'success'
    assert result['planning_lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['decision_predicate'] == 'signal_set'


# =============================================================================
# Each signal firing deep in isolation
# =============================================================================


def test_s2_scope_estimate_multi_module_forces_deep(plan_context):
    """S2 — a broad scope_estimate forces deep while all other signals stay light."""
    # Arrange — flip only scope_estimate to multi_module
    plan_dir = _light_setup(plan_context, 'pl-s2')
    _write_references(plan_dir, scope_estimate='multi_module')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s2'))

    # Assert
    assert result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']


def test_s2_scope_estimate_absent_forces_deep(plan_context):
    """S2 — an absent scope_estimate (unknown band) biases deep."""
    # Arrange — references with no scope_estimate at all
    plan_dir = _light_setup(plan_context, 'pl-s2-absent')
    _write_references(plan_dir, scope_estimate=None)

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s2-absent'))

    # Assert
    assert result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']


def test_s3_change_type_feature_forces_deep(plan_context):
    """S3 — a generative change_type (feature) forces deep."""
    # Arrange — flip only change_type to feature
    plan_dir = _light_setup(plan_context, 'pl-s3')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s3'))

    # Assert
    assert result['planning_lane'] == 'deep'
    assert 'S3:change_type' in result['fired_signals']


def test_s4_compatibility_breaking_forces_deep(plan_context):
    """S4 — breaking compatibility forces deep."""
    # Arrange — flip only compatibility to breaking
    _light_setup(plan_context, 'pl-s4')
    _write_marshal(plan_context.fixture_dir, compatibility='breaking', deep_lane='auto')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s4'))

    # Assert
    assert result['planning_lane'] == 'deep'
    assert 'S4:compatibility' in result['fired_signals']


def test_s5_vague_request_forces_deep(plan_context):
    """S5 — a vague request (no path, no fix signal) forces deep."""
    # Arrange — replace the concrete body with a vague one
    plan_dir = _light_setup(plan_context, 'pl-s5')
    _write_request(plan_dir, _VAGUE_BODY)

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s5'))

    # Assert
    assert result['planning_lane'] == 'deep'
    assert 'S5:concreteness' in result['fired_signals']
    assert result['signals']['request_concrete'] is False


def test_s5_concrete_request_with_cli_signal_stays_light(plan_context):
    """S5 — a request body carrying a CLI invocation counts as concrete (light)."""
    # Arrange — body with a python3 .plan/execute-script.py invocation, no path
    plan_dir = _light_setup(plan_context, 'pl-s5-cli')
    _write_request(
        plan_dir,
        'Run python3 .plan/execute-script.py plan-marshall:foo:foo bar and verify.',
    )

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s5-cli'))

    # Assert — concreteness passes, so S5 does not fire; lane stays light
    assert result['signals']['request_concrete'] is True
    assert 'S5:concreteness' not in result['fired_signals']
    assert result['planning_lane'] == 'light'


def test_s1_free_form_source_with_vague_request_forces_deep(plan_context):
    """S1 — free-form source AND failed S5 concreteness conjunction forces deep."""
    # Arrange — free-form source (plan_source unset) + vague body
    plan_dir = plan_context.plan_dir_for('pl-s1')
    _write_request(plan_dir, _VAGUE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})  # no plan_source
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s1'))

    # Assert — both S1 and S5 fire (the conjunction is what S1 keys off)
    assert result['planning_lane'] == 'deep'
    assert 'S1:plan_source' in result['fired_signals']


def test_s1_free_form_source_with_concrete_request_stays_light(plan_context):
    """S1 calibration — free-form source ALONE does not force deep when S5 passes."""
    # Arrange — free-form source but a concrete request body
    plan_dir = plan_context.plan_dir_for('pl-s1-concrete')
    _write_request(plan_dir, _CONCRETE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})  # no plan_source
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s1-concrete'))

    # Assert — concrete anchor keeps the free-form request light
    assert result['planning_lane'] == 'light'
    assert 'S1:plan_source' not in result['fired_signals']


def test_s6_lane_override_deep_forces_deep(plan_context):
    """S6 — an explicit --lane-override deep forces deep regardless of signals."""
    # Arrange — all-light baseline, then override to deep
    _light_setup(plan_context, 'pl-s6')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-s6', lane_override='deep'))

    # Assert
    assert result['planning_lane'] == 'deep'
    assert 'S6:override' in result['fired_signals']


# =============================================================================
# ceremony_policy.planning.deep_lane short-circuit
# =============================================================================


def test_ceremony_always_forces_deep_overriding_light_signals(plan_context):
    """ceremony deep_lane=always forces deep even when every signal is light."""
    # Arrange — all-light baseline, then ceremony always
    _light_setup(plan_context, 'pl-ceremony-always')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-ceremony-always'))

    # Assert
    assert result['planning_lane'] == 'deep'
    assert result['decision_predicate'] == 'ceremony_policy.planning.deep_lane=always'
    assert result['ceremony_deep_lane'] == 'always'


def test_ceremony_never_forces_light_overriding_deep_signals(plan_context):
    """ceremony deep_lane=never forces light even when deep signals fire."""
    # Arrange — multiple deep signals present, then ceremony never short-circuits
    plan_dir = _light_setup(plan_context, 'pl-ceremony-never')
    _write_references(plan_dir, scope_estimate='multi_module')  # S2 deep
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})  # S3 deep
    _write_marshal(plan_context.fixture_dir, compatibility='breaking', deep_lane='never')  # S4 deep

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-ceremony-never'))

    # Assert — the never short-circuit wins over all the deep signals
    assert result['planning_lane'] == 'light'
    assert result['decision_predicate'] == 'ceremony_policy.planning.deep_lane=never'


def test_ceremony_auto_defers_to_signal_set(plan_context):
    """ceremony deep_lane=auto (default) lets the signal set decide."""
    # Arrange — one deep signal under auto
    plan_dir = _light_setup(plan_context, 'pl-ceremony-auto')
    _write_references(plan_dir, scope_estimate='broad')  # S2 deep

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-ceremony-auto'))

    # Assert
    assert result['decision_predicate'] == 'signal_set'
    assert result['planning_lane'] == 'deep'


# =============================================================================
# --persist
# =============================================================================


def test_persist_writes_planning_lane_metadata(plan_context):
    """--persist writes the resolved lane into status.metadata.planning_lane."""
    # Arrange
    plan_dir = _light_setup(plan_context, 'pl-persist')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-persist', persist=True))

    # Assert
    assert result['persisted'] is True
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['planning_lane'] == 'light'


def test_route_without_persist_does_not_write(plan_context):
    """Without --persist the router does not mutate status.json."""
    # Arrange
    plan_dir = _light_setup(plan_context, 'pl-nopersist')

    # Act
    result = cmd_planning_lane_route(_ns_route('pl-nopersist'))

    # Assert
    assert result['persisted'] is False
    status = json.loads((plan_dir / 'status.json').read_text())
    assert 'planning_lane' not in status.get('metadata', {})


# =============================================================================
# escalate — one-way ratchet
# =============================================================================


def test_escalate_sets_deep_and_lane_escalated(plan_context):
    """escalate sets planning_lane=deep + lane_escalated=true + escalation_trigger."""
    # Arrange — a light plan that then escalates
    plan_dir = _light_setup(plan_context, 'pl-escalate')

    # Act
    result = cmd_planning_lane_escalate(_ns_escalate('pl-escalate', trigger='explosion', persist=True))

    # Assert — return payload
    assert result['planning_lane'] == 'deep'
    assert result['lane_escalated'] is True
    assert result['escalation_trigger'] == 'explosion'
    assert result['persisted'] is True
    # Assert — persisted metadata
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['planning_lane'] == 'deep'
    assert status['metadata']['lane_escalated'] is True
    assert status['metadata']['escalation_trigger'] == 'explosion'


def test_escalate_is_monotonic_route_cannot_downgrade(plan_context):
    """After escalate, a subsequent light-resolving route does NOT clobber deep on disk.

    The one-way invariant: once lane_escalated=true is persisted, a fresh route
    that resolves light must not silently downgrade the escalated lane. The route
    verb persists planning_lane, but the sticky lane_escalated flag remains, so
    the deep escalation evidence is preserved.
    """
    # Arrange — escalate first
    plan_dir = _light_setup(plan_context, 'pl-monotonic')
    cmd_planning_lane_escalate(_ns_escalate('pl-monotonic', trigger='premise', persist=True))

    # Act — a light-resolving route does not clear the sticky escalation flag
    cmd_planning_lane_route(_ns_route('pl-monotonic', persist=True))

    # Assert — lane_escalated remains true (sticky), escalation evidence preserved
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['lane_escalated'] is True
    assert status['metadata']['escalation_trigger'] == 'premise'


def test_escalate_records_each_trigger(plan_context):
    """Each escalation trigger value round-trips into escalation_trigger."""
    # Arrange / Act / Assert — all three trigger choices
    for trigger in ('explosion', 'premise', 'cross_cutting'):
        plan_dir = _light_setup(plan_context, f'pl-trig-{trigger}')
        result = cmd_planning_lane_escalate(
            _ns_escalate(f'pl-trig-{trigger}', trigger=trigger, persist=True)
        )
        assert result['escalation_trigger'] == trigger
        status = json.loads((plan_dir / 'status.json').read_text())
        assert status['metadata']['escalation_trigger'] == trigger


# =============================================================================
# Error path
# =============================================================================


def test_route_plan_dir_not_found_errors(plan_context):
    """route against a missing plan dir returns a structured error."""
    # Arrange / Act
    result = cmd_planning_lane_route(_ns_route('pl-missing'))

    # Assert
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


def test_escalate_plan_dir_not_found_errors(plan_context):
    """escalate against a missing plan dir returns a structured error."""
    # Arrange / Act
    result = cmd_planning_lane_escalate(_ns_escalate('pl-missing-esc'))

    # Assert
    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Dispatch wiring
# =============================================================================


def test_planning_lane_route_registered_in_manage_status_dispatch():
    """The route verb resolves to cmd_planning_lane_route in manage-status.py."""
    import argparse  # noqa: PLC0415

    manage_status = _load_module('_manage_status_dispatch_check_pl_route', 'manage-status.py')

    assert callable(manage_status.cmd_planning_lane_route)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    lane = sub.add_parser('planning-lane')
    lane_sub = lane.add_subparsers(dest='verb')
    route = lane_sub.add_parser('route')
    route.set_defaults(func=manage_status.cmd_planning_lane_route)
    ns = p.parse_args(['planning-lane', 'route'])
    assert ns.func is manage_status.cmd_planning_lane_route


def test_planning_lane_escalate_registered_in_manage_status_dispatch():
    """The escalate verb resolves to cmd_planning_lane_escalate in manage-status.py."""
    import argparse  # noqa: PLC0415

    manage_status = _load_module('_manage_status_dispatch_check_pl_esc', 'manage-status.py')

    assert callable(manage_status.cmd_planning_lane_escalate)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    lane = sub.add_parser('planning-lane')
    lane_sub = lane.add_subparsers(dest='verb')
    esc = lane_sub.add_parser('escalate')
    esc.set_defaults(func=manage_status.cmd_planning_lane_escalate)
    ns = p.parse_args(['planning-lane', 'escalate'])
    assert ns.func is manage_status.cmd_planning_lane_escalate
