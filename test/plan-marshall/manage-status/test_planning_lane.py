#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Tests for the ``planning-lane`` subcommand of manage-status.

The router resolves ``planning_lane ∈ {light, deep}`` from the DQ1 signal set
(S1–S6) plus a ``request.md`` regex, with zero codebase discovery. The default
is ``light``; any deep-precondition signal forces ``deep``; the
``plan.phase-1-init.deep_lane`` (``always``/``never``/``auto``) gate
short-circuits the signal evaluation. The ``escalate`` verb is a one-way
light→deep ratchet that refuses any downgrade.

Coverage:
- Each signal (S1–S6) firing deep in isolation.
- The all-light default (no deep signal fires).
- The deep_lane ``always`` / ``never`` short-circuit.
- ``--lane-override`` handling.
- ``--persist`` writes status.metadata.planning_lane.
- The one-way escalate invariant (deep + lane_escalated, no downgrade).
- Dispatch wiring (both verbs registered in manage-status.py argparse).
- ``evaluate_signals_pure`` — direct, I/O-free unit coverage of the extracted
  pure scorer: each of the five signal arguments firing deep in isolation, the
  all-light default, the S6 override, and the importability of the S5 regex
  constants and ``_request_is_concrete`` for downstream consumers.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

import pytest

from conftest import load_script_module

_mod = load_script_module(
    'plan-marshall', 'manage-status', '_cmd_planning_lane.py', '_cmd_planning_lane_under_test'
)
cmd_planning_lane_route = _mod.cmd_planning_lane_route
cmd_planning_lane_escalate = _mod.cmd_planning_lane_escalate
evaluate_signals_pure = _mod.evaluate_signals_pure


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
        'plan': {
            'phase-1-init': {'deep_lane': deep_lane},
            'phase-2-refine': {'compatibility': compatibility},
        },
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
    _light_setup(plan_context, 'pl-light')

    result = cmd_planning_lane_route(_ns_route('pl-light'))

    assert result['status'] == 'success'
    assert result['planning_lane'] == 'light'
    assert result['fired_signals'] == []
    assert result['decision_predicate'] == 'signal_set'


# =============================================================================
# Each signal firing deep in isolation
# =============================================================================


def test_s2_scope_estimate_multi_module_forces_deep(plan_context):
    """S2 — a broad scope_estimate forces deep while all other signals stay light."""
    # Flip only scope_estimate to multi_module.
    plan_dir = _light_setup(plan_context, 'pl-s2')
    _write_references(plan_dir, scope_estimate='multi_module')

    result = cmd_planning_lane_route(_ns_route('pl-s2'))

    assert result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']


def test_s2_scope_estimate_absent_forces_deep(plan_context):
    """S2 — an absent scope_estimate (unknown band) biases deep."""
    # References with no scope_estimate at all.
    plan_dir = _light_setup(plan_context, 'pl-s2-absent')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_planning_lane_route(_ns_route('pl-s2-absent'))

    assert result['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in result['fired_signals']


def test_s3_change_type_feature_forces_deep(plan_context):
    """S3 — a generative change_type (feature) forces deep."""
    # Flip only change_type to feature.
    plan_dir = _light_setup(plan_context, 'pl-s3')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})

    result = cmd_planning_lane_route(_ns_route('pl-s3'))

    assert result['planning_lane'] == 'deep'
    assert 'S3:change_type' in result['fired_signals']


def test_s4_compatibility_breaking_forces_deep(plan_context):
    """S4 — breaking compatibility forces deep."""
    # Flip only compatibility to breaking.
    _light_setup(plan_context, 'pl-s4')
    _write_marshal(plan_context.fixture_dir, compatibility='breaking', deep_lane='auto')

    result = cmd_planning_lane_route(_ns_route('pl-s4'))

    assert result['planning_lane'] == 'deep'
    assert 'S4:compatibility' in result['fired_signals']


def test_s5_vague_request_forces_deep(plan_context):
    """S5 — a vague request (no path, no fix signal) forces deep."""
    # Replace the concrete body with a vague one.
    plan_dir = _light_setup(plan_context, 'pl-s5')
    _write_request(plan_dir, _VAGUE_BODY)

    result = cmd_planning_lane_route(_ns_route('pl-s5'))

    assert result['planning_lane'] == 'deep'
    assert 'S5:concreteness' in result['fired_signals']
    assert result['signals']['request_concrete'] is False


def test_s5_concrete_request_with_cli_signal_stays_light(plan_context):
    """S5 — a request body carrying a CLI invocation counts as concrete (light)."""
    # Body with a python3 .plan/execute-script.py invocation, no path.
    plan_dir = _light_setup(plan_context, 'pl-s5-cli')
    _write_request(
        plan_dir,
        'Run python3 .plan/execute-script.py plan-marshall:foo:foo bar and verify.',
    )

    result = cmd_planning_lane_route(_ns_route('pl-s5-cli'))

    # Concreteness passes, so S5 does not fire; lane stays light.
    assert result['signals']['request_concrete'] is True
    assert 'S5:concreteness' not in result['fired_signals']
    assert result['planning_lane'] == 'light'


def test_s1_free_form_source_with_vague_request_forces_deep(plan_context):
    """S1 — free-form source AND failed S5 concreteness conjunction forces deep."""
    # Free-form source (plan_source unset) + vague body.
    plan_dir = plan_context.plan_dir_for('pl-s1')
    _write_request(plan_dir, _VAGUE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})  # no plan_source
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    result = cmd_planning_lane_route(_ns_route('pl-s1'))

    # Both S1 and S5 fire (the conjunction is what S1 keys off).
    assert result['planning_lane'] == 'deep'
    assert 'S1:plan_source' in result['fired_signals']


def test_s1_free_form_source_with_concrete_request_stays_light(plan_context):
    """S1 calibration — free-form source ALONE does not force deep when S5 passes."""
    # Free-form source but a concrete request body.
    plan_dir = plan_context.plan_dir_for('pl-s1-concrete')
    _write_request(plan_dir, _CONCRETE_BODY)
    _write_status(plan_dir, metadata={'change_type': 'bug_fix'})  # no plan_source
    _write_references(plan_dir, scope_estimate='surgical')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    result = cmd_planning_lane_route(_ns_route('pl-s1-concrete'))

    # Concrete anchor keeps the free-form request light.
    assert result['planning_lane'] == 'light'
    assert 'S1:plan_source' not in result['fired_signals']


def test_s6_lane_override_deep_forces_deep(plan_context):
    """S6 — an explicit --lane-override deep forces deep regardless of signals."""
    # All-light baseline, then override to deep.
    _light_setup(plan_context, 'pl-s6')

    result = cmd_planning_lane_route(_ns_route('pl-s6', lane_override='deep'))

    assert result['planning_lane'] == 'deep'
    assert 'S6:override' in result['fired_signals']


# =============================================================================
# plan.phase-1-init.deep_lane short-circuit
# =============================================================================


def test_deep_lane_always_forces_deep_overriding_light_signals(plan_context):
    """deep_lane=always forces deep even when every signal is light."""
    # All-light baseline, then deep_lane always.
    _light_setup(plan_context, 'pl-deep-lane-always')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    result = cmd_planning_lane_route(_ns_route('pl-deep-lane-always'))

    assert result['planning_lane'] == 'deep'
    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=always'
    assert result['ceremony_deep_lane'] == 'always'


def test_deep_lane_never_forces_light_overriding_deep_signals(plan_context):
    """deep_lane=never forces light even when deep signals fire."""
    # Multiple deep signals present, then deep_lane never short-circuits.
    plan_dir = _light_setup(plan_context, 'pl-deep-lane-never')
    _write_references(plan_dir, scope_estimate='multi_module')  # S2 deep
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})  # S3 deep
    _write_marshal(plan_context.fixture_dir, compatibility='breaking', deep_lane='never')  # S4 deep

    result = cmd_planning_lane_route(_ns_route('pl-deep-lane-never'))

    # The never short-circuit wins over all the deep signals.
    assert result['planning_lane'] == 'light'
    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=never'


def test_deep_lane_auto_defers_to_signal_set(plan_context):
    """deep_lane=auto (default) lets the signal set decide."""
    # One deep signal under auto.
    plan_dir = _light_setup(plan_context, 'pl-deep-lane-auto')
    _write_references(plan_dir, scope_estimate='broad')  # S2 deep

    result = cmd_planning_lane_route(_ns_route('pl-deep-lane-auto'))

    assert result['decision_predicate'] == 'signal_set'
    assert result['planning_lane'] == 'deep'


# =============================================================================
# --persist
# =============================================================================


def test_persist_writes_planning_lane_metadata(plan_context):
    """--persist writes the resolved lane into status.metadata.planning_lane."""
    plan_dir = _light_setup(plan_context, 'pl-persist')

    result = cmd_planning_lane_route(_ns_route('pl-persist', persist=True))

    assert result['persisted'] is True
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['planning_lane'] == 'light'


def test_route_without_persist_does_not_write(plan_context):
    """Without --persist the router does not mutate status.json."""
    plan_dir = _light_setup(plan_context, 'pl-nopersist')

    result = cmd_planning_lane_route(_ns_route('pl-nopersist'))

    assert result['persisted'] is False
    status = json.loads((plan_dir / 'status.json').read_text())
    assert 'planning_lane' not in status.get('metadata', {})


# =============================================================================
# escalate — one-way ratchet
# =============================================================================


def test_escalate_sets_deep_and_lane_escalated(plan_context):
    """escalate sets planning_lane=deep + lane_escalated=true + escalation_trigger."""
    # A light plan that then escalates.
    plan_dir = _light_setup(plan_context, 'pl-escalate')

    result = cmd_planning_lane_escalate(_ns_escalate('pl-escalate', trigger='explosion', persist=True))

    # Return payload.
    assert result['planning_lane'] == 'deep'
    assert result['lane_escalated'] is True
    assert result['escalation_trigger'] == 'explosion'
    assert result['persisted'] is True
    # Persisted metadata.
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
    # Escalate first.
    plan_dir = _light_setup(plan_context, 'pl-monotonic')
    cmd_planning_lane_escalate(_ns_escalate('pl-monotonic', trigger='premise', persist=True))

    # A light-resolving route does not clear the sticky escalation flag.
    cmd_planning_lane_route(_ns_route('pl-monotonic', persist=True))

    # lane_escalated remains true (sticky), escalation evidence preserved.
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['lane_escalated'] is True
    assert status['metadata']['escalation_trigger'] == 'premise'


@pytest.mark.parametrize('trigger', ['explosion', 'premise', 'cross_cutting'])
def test_escalate_records_each_trigger(plan_context, trigger):
    """Each escalation trigger value round-trips into escalation_trigger."""
    plan_dir = _light_setup(plan_context, f'pl-trig-{trigger}')

    result = cmd_planning_lane_escalate(_ns_escalate(f'pl-trig-{trigger}', trigger=trigger, persist=True))

    assert result['escalation_trigger'] == trigger
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['escalation_trigger'] == trigger


# =============================================================================
# Error path
# =============================================================================


def test_route_plan_dir_not_found_errors(plan_context):
    """route against a missing plan dir returns a structured error."""
    result = cmd_planning_lane_route(_ns_route('pl-missing'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


def test_escalate_plan_dir_not_found_errors(plan_context):
    """escalate against a missing plan dir returns a structured error."""
    result = cmd_planning_lane_escalate(_ns_escalate('pl-missing-esc'))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# Dispatch wiring
# =============================================================================


def test_planning_lane_route_registered_in_manage_status_dispatch():
    """The route verb resolves to cmd_planning_lane_route in manage-status.py."""
    import argparse  # noqa: PLC0415

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check_pl_route'
    )

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

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check_pl_esc'
    )

    assert callable(manage_status.cmd_planning_lane_escalate)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    lane = sub.add_parser('planning-lane')
    lane_sub = lane.add_subparsers(dest='verb')
    esc = lane_sub.add_parser('escalate')
    esc.set_defaults(func=manage_status.cmd_planning_lane_escalate)
    ns = p.parse_args(['planning-lane', 'escalate'])
    assert ns.func is manage_status.cmd_planning_lane_escalate


# =============================================================================
# evaluate_signals_pure — direct, I/O-free unit coverage
# =============================================================================
#
# The pure scorer takes the five realized signals (plus the S6 override) as plain
# arguments and performs zero file I/O. These cases lock its scoring against the
# integrated _evaluate_signals path covered above. The all-light baseline below
# biases EVERY signal light; each isolation case flips exactly one argument and
# asserts the resulting lane + fired_signals entry.

# All-light keyword baseline: surgical scope, bug_fix change_type, deprecation
# compatibility, pre-specified source, concrete request, no override.
_LIGHT_PURE_KWARGS = {
    'scope_estimate': 'surgical',
    'change_type': 'bug_fix',
    'compatibility': 'deprecation',
    'plan_source': 'lesson',
    'request_concrete': True,
    'override': None,
}


def _pure(**overrides):
    """Score evaluate_signals_pure from the all-light baseline with overrides applied."""
    kwargs = {**_LIGHT_PURE_KWARGS, **overrides}
    return evaluate_signals_pure(**kwargs)


def test_pure_all_light_signals_resolve_light():
    """No signal fires → the pure scorer resolves the light default."""
    result = _pure()

    assert result['lane'] == 'light'
    assert result['fired_signals'] == []


@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad', 'none'])
def test_pure_s2_deep_scope_estimate_fires_deep(scope_estimate):
    """S2 — each deep scope band fires S2 in isolation."""
    result = _pure(scope_estimate=scope_estimate)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate']


def test_pure_s2_absent_scope_estimate_fires_deep():
    """S2 — an absent (None) scope_estimate biases deep."""
    result = _pure(scope_estimate=None)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S2:scope_estimate']


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
def test_pure_s3_generative_change_type_fires_deep(change_type):
    """S3 — each generative change_type fires S3 in isolation."""
    result = _pure(change_type=change_type)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S3:change_type']


def test_pure_s4_breaking_compatibility_fires_deep():
    """S4 — breaking compatibility fires S4 in isolation."""
    result = _pure(compatibility='breaking')

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S4:compatibility']


def test_pure_s5_non_concrete_request_fires_deep():
    """S5 — a non-concrete request fires S5 in isolation."""
    result = _pure(request_concrete=False)

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S5:concreteness']


@pytest.mark.parametrize('plan_source', [None, '', 'free_form', 'cli'])
def test_pure_s1_free_form_source_with_non_concrete_request_fires_deep(plan_source):
    """S1 — free-form source AND failed concreteness conjunction fires S1 (and S5)."""
    result = _pure(plan_source=plan_source, request_concrete=False)

    assert result['lane'] == 'deep'
    # The S1 conjunction keys off the failed S5 concreteness, so both fire.
    assert 'S1:plan_source' in result['fired_signals']
    assert 'S5:concreteness' in result['fired_signals']


@pytest.mark.parametrize('plan_source', [None, '', 'free_form', 'cli'])
def test_pure_s1_free_form_source_with_concrete_request_stays_light(plan_source):
    """S1 — free-form source ALONE does not fire when the request is concrete."""
    result = _pure(plan_source=plan_source, request_concrete=True)

    assert result['lane'] == 'light'
    assert 'S1:plan_source' not in result['fired_signals']


def test_pure_s6_override_deep_fires_deep():
    """S6 — an explicit deep override fires S6 in isolation."""
    result = _pure(override='deep')

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == ['S6:override']


def test_pure_s6_override_light_does_not_force_deep():
    """S6 — a light override does not fire (the override is one-way to deep)."""
    result = _pure(override='light')

    assert result['lane'] == 'light'
    assert 'S6:override' not in result['fired_signals']


def test_pure_signals_echoes_all_realized_values():
    """The returned ``signals`` dict echoes every realized signal value verbatim."""
    result = _pure(
        scope_estimate='multi_module',
        change_type='feature',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=False,
        override='deep',
    )

    assert result['signals'] == {
        'plan_source': 'lesson',
        'scope_estimate': 'multi_module',
        'change_type': 'feature',
        'compatibility': 'breaking',
        'request_concrete': False,
        'planning_lane_override': 'deep',
    }


def test_pure_multiple_deep_signals_accumulate_in_fired_order():
    """Multiple deep signals all appear in fired_signals in canonical S1..S6 order."""
    result = _pure(
        scope_estimate='multi_module',  # S2
        change_type='feature',           # S3
        compatibility='breaking',        # S4
    )

    assert result['lane'] == 'deep'
    assert result['fired_signals'] == [
        'S2:scope_estimate',
        'S3:change_type',
        'S4:compatibility',
    ]


def test_pure_override_defaults_to_none_when_omitted():
    """The override argument is optional and defaults to None (no S6)."""
    result = evaluate_signals_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )

    assert result['lane'] == 'light'
    assert result['signals']['planning_lane_override'] is None


# =============================================================================
# S5 regex constants + _request_is_concrete importability (downstream consumers)
# =============================================================================
#
# The audit retrospective check (deliverable 2) re-derives request_concrete from
# each archived request.md by importing these symbols. These tests lock that they
# remain module-level and importable, and that _request_is_concrete matches the
# documented S5 anchors.


def test_s5_regex_constants_are_module_level_importable():
    """The four S5 regexes are importable module-level compiled patterns."""
    import re  # noqa: PLC0415

    for name in ('_PATH_RE', '_FENCE_RE', '_CLI_RE', '_NOTATION_RE'):
        pattern = getattr(_mod, name)
        assert isinstance(pattern, re.Pattern), f'{name} must be a compiled regex'


def test_request_is_concrete_is_module_level_importable():
    """_request_is_concrete is importable for downstream re-derivation of S5."""
    assert callable(_mod._request_is_concrete)


@pytest.mark.parametrize(
    'body',
    [
        'Update `marketplace/bundles/plan-marshall/skills/x/scripts/x.py` to fix it.',
        'Run python3 .plan/execute-script.py plan-marshall:foo:foo bar.',
        'Use the manage-status verb to read the plan.',
        'Here is a fenced block:\n```\ncode\n```\n',
    ],
)
def test_request_is_concrete_true_for_each_anchor(body):
    """Each S5 anchor (path / CLI / notation / fence) marks the body concrete."""
    assert _mod._request_is_concrete(body) is True


@pytest.mark.parametrize('body', ['', 'The thing should do the thing, somehow.'])
def test_request_is_concrete_false_for_anchorless_body(body):
    """An empty or anchorless body is not concrete (→ S5 deep)."""
    assert _mod._request_is_concrete(body) is False
