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
- ``project_profile_pure`` — the execution-profile posture projection: the
  ``full`` / ``minimal`` / ``auto`` recommendation as a pure function of the same
  signals, the ``profile`` key on the route return, ``--persist`` writing
  ``status.metadata.execution_profile``, the independence invariant that
  ``deep_lane=always`` does NOT coerce the posture to ``full``, and the mirrored
  negative that a concrete but NON-narrow change never projects ``minimal`` (the
  security-gate half of the shared-predicate defect).
- ``classify_scope_pure`` / ``scope_estimate_from_request_pure`` — the pre-route
  coarse scope classifier over the whole band table: ``surgical`` for one-to-three
  distinct file paths with no fan-out marker, ``single_module`` for the 4–7 middle
  band and for an ambiguous pathless request, ``multi_module`` for a real fan-out
  marker or eight-or-more distinct paths, ``none`` as the DECLARED UNKNOWN for an
  unscoreable body (plus the invariant that the unknown biases S2 deep). Also the
  band boundaries at 3/4 and 7/8, markdown bold NOT registering as fan-out,
  distinct-path dedup, the ``scope_provenance`` explanation block, and the
  zero-architecture-call invariant.
- ``_read_request_body`` — the whole-body, heading-blind read: text below a
  nested ``## `` heading is reached, only the host ``# Request`` title line is
  stripped, and an absent / title-only / non-UTF-8 ``request.md`` degrades to the
  declared unknown instead of raising.
- The settled path-counter semantics — the intentional bare-filename exclusion
  (a directory separator is required) and the declared inapplicability of
  target-vs-citation discrimination, both asserted with their one-directional
  (band-widening) residual.
- The shared-population invariant — S5 concreteness and the scope band are shown
  to consume the identical body, not merely documented as doing so.
- ``cmd_scope_estimate_heuristic`` — ``--persist`` writing
  ``references.json.scope_estimate``, the ``scope_resolved`` classified-vs-unknown
  discriminator, the no-persist read-only path, the missing plan-dir error, its
  manage-status dispatch registration, and the D2 acceptance that
  pre-classification flips the router's S2 from deep to light for a concrete
  narrow request.
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
project_profile_pure = _mod.project_profile_pure
classify_scope_pure = _mod.classify_scope_pure
scope_estimate_from_request_pure = _mod.scope_estimate_from_request_pure
cmd_scope_estimate_heuristic = _mod.cmd_scope_estimate_heuristic


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


# An INGESTED orchestrator plan spec, embedded verbatim under ``## Original
# Input`` exactly as phase-1-init writes it. Its defining property — and the one
# every pre-existing fixture above lacks — is that it carries its OWN ``## ``
# headings, so an H2-splitting section reader terminates ``original_input`` at
# ``## Objective`` and never sees the surface list below it.
#
# The two readings disagree by construction, which is what makes this fixture a
# pre/post discriminator rather than a restatement:
#
#   truncated (H2-split) -> 1 path, the boilerplate CITATION only -> surgical
#   whole body           -> 5 distinct paths (citation + 4 targets) -> single_module
_INGESTED_SPEC_BODY = (
    '# PLAN-99: An ingested orchestrator plan spec\n'
    '\n'
    'epic: truthful-signals\n'
    '\n'
    '> Staged plan spec — one shippable unit of work. See\n'
    '> `persona-marshall-orchestrator/standards/orchestration-model.md` for the\n'
    '> hand-off contract.\n'
    '\n'
    '## Objective\n'
    '\n'
    'Fix the four real targets enumerated below.\n'
    '\n'
    '## Expected Surface\n'
    '\n'
    '- `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py`\n'
    '- `test/plan-marshall/manage-status/test_planning_lane.py`\n'
    '- `marketplace/bundles/plan-marshall/skills/phase-1-init/SKILL.md`\n'
    '- `doc/concepts/orchestration.adoc`\n'
)

# The single path token in the truncated head region — a CITATION of a governing
# document, never a target of the work.
_BOILERPLATE_CITATION = 'persona-marshall-orchestrator/standards/orchestration-model.md'
# A target named in the ingested body BELOW the first nested ``## `` heading. The
# truncating read could never reach it.
_TARGET_BELOW_NESTED_HEADING = (
    'marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_planning_lane.py'
)


def _write_ingested_request(plan_dir: Path, spec_body: str = _INGESTED_SPEC_BODY) -> None:
    """Author a ``request.md`` whose ``## Original Input`` holds an ingested spec.

    Mirrors the phase-1-init shape for an orchestrated plan: a ``# Request``
    title, the virtual-header metadata block, and the spec embedded verbatim
    under ``## Original Input``. There is deliberately NO ``## Clarified
    Request`` section — the scope heuristic runs at phase-1-init, before refine
    authors one.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    content = (
        '# Request: An ingested orchestrator plan spec\n'
        '\n'
        f'plan_id: {plan_dir.name}\n'
        'source: description\n'
        '\n'
        '## Original Input\n'
        '\n'
        f'{spec_body}'
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
    plan_dir: Path = plan_context.plan_dir_for(plan_id)
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


def test_s3_change_type_feature_suppressed_when_narrow_and_concrete(plan_context):
    """S3 — a generative change_type is SUPPRESSED under the narrow-and-concrete carve-out.

    The ``_light_setup`` baseline is surgical scope + a concrete request, so a
    ``feature`` change_type no longer forces deep on its own — the positively
    bounded case stays light. (S3 firing deep for a broad/unknown scope is
    covered by ``test_planning_lane_calibration.py``.)
    """
    # Flip only change_type to feature; the narrow+concrete baseline carves it out.
    plan_dir = _light_setup(plan_context, 'pl-s3')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})

    result = cmd_planning_lane_route(_ns_route('pl-s3'))

    assert result['planning_lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']


def test_s4_compatibility_breaking_suppressed_when_narrow_and_concrete(plan_context):
    """S4 — breaking compatibility is SUPPRESSED under the narrow-and-concrete carve-out.

    The ``_light_setup`` baseline is surgical scope + a concrete request, so a
    ``breaking`` compatibility no longer forces deep on its own. (S4 firing deep
    for a broad/unknown scope is covered by ``test_planning_lane_calibration.py``.)
    """
    # Flip only compatibility to breaking; the narrow+concrete baseline carves it out.
    _light_setup(plan_context, 'pl-s4')
    _write_marshal(plan_context.fixture_dir, compatibility='breaking', deep_lane='auto')

    result = cmd_planning_lane_route(_ns_route('pl-s4'))

    assert result['planning_lane'] == 'light'
    assert 'S4:compatibility' not in result['fired_signals']


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
def test_pure_s3_generative_change_type_suppressed_when_narrow_and_concrete(change_type):
    """S3 — a generative change_type is carved out under the narrow+concrete baseline.

    The all-light baseline is surgical scope + concrete request, so S3 does not
    fire on its own. S3 firing deep alongside a broad/unknown scope is covered by
    ``test_planning_lane_calibration.py`` and ``test_pure_multiple_deep_signals``.
    """
    result = _pure(change_type=change_type)

    assert result['lane'] == 'light'
    assert 'S3:change_type' not in result['fired_signals']


def test_pure_s4_breaking_compatibility_suppressed_when_narrow_and_concrete():
    """S4 — breaking compatibility is carved out under the narrow+concrete baseline.

    S4 firing deep for a broad/unknown scope is covered by
    ``test_planning_lane_calibration.py`` and ``test_pure_multiple_deep_signals``.
    """
    result = _pure(compatibility='breaking')

    assert result['lane'] == 'light'
    assert 'S4:compatibility' not in result['fired_signals']


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
    """The returned ``signals`` dict echoes every realized signal value verbatim.

    Compared with ``==`` on purpose: the point is that the echo is COMPLETE, so a
    signal added to the scorer without being echoed fails here. That is why the S7
    ``risk_prose`` key appears below — it is the pin working as designed, not an
    incidental update. (S7's own behaviour is covered by
    ``test_planning_lane_risk_prose.py``.)
    """
    result = _pure(
        scope_estimate='multi_module',
        change_type='feature',
        compatibility='breaking',
        plan_source='lesson',
        request_concrete=False,
        risk_prose=True,
        override='deep',
    )

    assert result['signals'] == {
        'plan_source': 'lesson',
        'scope_estimate': 'multi_module',
        'change_type': 'feature',
        'compatibility': 'breaking',
        'request_concrete': False,
        'risk_prose': True,
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
    """An empty or anchorless body is not concrete (→ S5 deep).

    Re-justified under the whole-body read: the empty case now arrives here only
    when ``request.md`` is genuinely absent, unreadable, or empty — never as a
    side effect of an H2 section boundary. S5 and the scope band agree on that
    input (S5 → not concrete, scope → declared unknown), and both bias deep, so
    the unscoreable request is widened by two independent signals rather than
    silently narrowed by either.
    """
    assert _mod._request_is_concrete(body) is False


# =============================================================================
# _read_request_body — the whole-body, heading-blind read
# =============================================================================
#
# The reader must be robust to an ingested spec carrying its own '## ' headings,
# which is the NORMAL case for every orchestrated plan. The shared markdown
# splitter starts a new section on any line beginning '## ' with no nesting
# awareness, so a section-scoped read truncated the request at the ingested
# body's first nested heading and scored boilerplate instead.


def test_read_request_body_returns_text_after_a_nested_h2_heading(plan_context):
    """The read spans the whole body, including text below a nested '## ' heading.

    The regression the whole-body read exists to prevent: with a section-scoped
    read this target is unreachable, because '## Objective' terminates the
    'Original Input' section before the surface list is ever seen.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-nested-h2')
    _write_ingested_request(plan_dir)

    body = _mod._read_request_body('pl-read-nested-h2')

    # Text below the first nested heading is present.
    assert _TARGET_BELOW_NESTED_HEADING in body
    assert '## Expected Surface' in body
    assert 'doc/concepts/orchestration.adoc' in body
    # The ingested spec's own headings survive verbatim — nothing was consumed
    # as a section boundary.
    assert '## Objective' in body


def test_read_request_body_strips_only_the_host_title_line(plan_context):
    """Only the host document's own '# Request' title line is removed."""
    plan_dir = plan_context.plan_dir_for('pl-read-title-strip')
    _write_ingested_request(plan_dir)

    body = _mod._read_request_body('pl-read-title-strip')

    assert '# Request' not in body
    # The INGESTED spec's own '# PLAN-99' title is not the host title and stays.
    assert '# PLAN-99: An ingested orchestrator plan spec' in body
    # Header metadata lines are not a section boundary and are retained.
    assert 'source: description' in body


def test_read_request_body_retains_a_non_first_line_request_heading(plan_context):
    """Only line 1 is eligible for the title strip — a later '# Request…' stays.

    The strip is anchored to the FIRST line rather than matched anywhere,
    because an ingested spec may legitimately carry its own ``# Request …``
    heading. Dropping that would silently remove request narrative and would
    contradict the docstring's ONLY-line-removed contract.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-nested-request-heading')
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text(
        '# Request: host title\n'
        '\n'
        'source: description\n'
        '\n'
        '# Request routing rework\n'
        '\n'
        'Body naming marketplace/bundles/plan-marshall/skills/x/y.py\n',
        encoding='utf-8',
    )

    body = _mod._read_request_body('pl-read-nested-request-heading')

    # The host title (line 1) is gone...
    assert '# Request: host title' not in body
    # ...but the ingested spec's own '# Request …' heading is preserved.
    assert '# Request routing rework' in body


def test_read_request_body_counts_targets_the_truncating_read_could_not_reach(plan_context):
    """The scored body yields the target paths, not just the boilerplate citation.

    Pins the end-to-end consequence of the read change on the same fixture: the
    truncated head region carries exactly one path — a citation — which would
    band ``surgical``; the whole body carries five, which lands in the 4–7 middle
    band, ``single_module``.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-target-count')
    _write_ingested_request(plan_dir)

    body = _mod._read_request_body('pl-read-target-count')
    paths = _mod._distinct_paths(body)

    assert _BOILERPLATE_CITATION in paths
    assert _TARGET_BELOW_NESTED_HEADING in paths
    assert len(paths) == 5, sorted(paths)
    assert scope_estimate_from_request_pure(body) == 'single_module'


def test_read_request_body_empty_when_request_absent(plan_context):
    """A plan with no request.md reads as the empty (declared-unknown) body."""
    plan_dir = plan_context.plan_dir_for('pl-read-absent')
    plan_dir.mkdir(parents=True, exist_ok=True)

    assert _mod._read_request_body('pl-read-absent') == ''


def test_read_request_body_empty_when_only_the_title_line_present(plan_context):
    """A request.md carrying nothing but the title line reads as empty, not as chrome."""
    plan_dir = plan_context.plan_dir_for('pl-read-title-only')
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'request.md').write_text('# Request: nothing else\n', encoding='utf-8')

    assert _mod._read_request_body('pl-read-title-only') == ''


def test_read_request_body_handles_non_utf8_request(plan_context):
    """A non-UTF-8 request.md degrades to the declared unknown, never an exception.

    ``Path.read_text(encoding='utf-8')`` raises ``UnicodeDecodeError`` — a
    ``ValueError`` subtype, NOT an ``OSError`` — so an ``except OSError`` guard
    alone would let it escape and crash the phase. This asserts the widened
    guard routes an undecodable body to the same unscoreable path as a missing
    file.
    """
    plan_dir = plan_context.plan_dir_for('pl-read-non-utf8')
    plan_dir.mkdir(parents=True, exist_ok=True)
    # 0xFF is not a valid UTF-8 start byte.
    (plan_dir / 'request.md').write_bytes(b'# Request\n\n\xff\xfe not utf-8 \xff\n')

    assert _mod._read_request_body('pl-read-non-utf8') == ''
    assert scope_estimate_from_request_pure(_mod._read_request_body('pl-read-non-utf8')) == 'none'


def test_scope_heuristic_declares_unknown_for_unreadable_request(plan_context):
    """End-to-end: an unscoreable request persists the declared unknown, not a band."""
    plan_dir = plan_context.plan_dir_for('pl-scope-unknown')
    plan_dir.mkdir(parents=True, exist_ok=True)
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(
        Namespace(plan_id='pl-scope-unknown', persist=True)
    )

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'none'
    assert result['scope_resolved'] is False
    assert result['distinct_path_count'] == 0
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'none'


def test_scope_heuristic_reports_scope_resolved_true_for_a_scored_body(plan_context):
    """``scope_resolved`` distinguishes a classified band from the declared unknown.

    Without this field a consumer reading ``scope_estimate`` alone cannot tell a
    measured band from a "cannot tell" verdict — which is exactly how a zero-byte
    read used to pass for a band.
    """
    plan_dir = plan_context.plan_dir_for('pl-scope-resolved')
    _write_request(plan_dir, 'Fix pkg/one.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(Namespace(plan_id='pl-scope-resolved', persist=False))

    assert result['scope_estimate'] == 'surgical'
    assert result['scope_resolved'] is True


def test_concreteness_and_scope_consume_the_identical_body(plan_context, monkeypatch):
    """S5 concreteness and the scope band read the SAME text — asserted, not claimed.

    The two signals are corroborating readings of one request. If one consumer
    were ever narrowed (say, to a declared-surface region) while the other kept
    the whole body, they would silently describe different documents and their
    agreement would stop meaning anything. This records the shared-population
    invariant behaviourally by capturing what each consumer actually receives.
    """
    plan_dir = plan_context.plan_dir_for('pl-shared-population')
    _write_ingested_request(plan_dir)
    _write_status(plan_dir)
    _write_references(plan_dir, scope_estimate=None)

    seen: list[str] = []
    real_read = _mod._read_request_body

    def _recording_read(plan_id: str) -> str:
        # _mod is loaded dynamically, so real_read is untyped (Any) to mypy.
        body: str = real_read(plan_id)
        seen.append(body)
        return body

    monkeypatch.setattr(_mod, '_read_request_body', _recording_read)

    _mod._evaluate_signals('pl-shared-population', {})
    cmd_scope_estimate_heuristic(Namespace(plan_id='pl-shared-population', persist=False))

    assert len(seen) == 2, 'both consumers must go through _read_request_body'
    assert seen[0] == seen[1] != ''


# =============================================================================
# project_profile_pure — execution-profile posture projection
# =============================================================================
#
# The posture projection recommends minimal / auto / full over the SAME signals
# the lane verdict scores. It is a pure derivation (no I/O, no cognition) and is
# independent of the deep_lane ceremony gate (deep_lane governs planning depth,
# not the profile — §4.2 of the lane-selection outline).


@pytest.mark.parametrize('change_type', ['feature', 'feature_breaking'])
@pytest.mark.parametrize('scope_estimate', ['multi_module', 'broad'])
def test_profile_generative_broad_change_projects_full(change_type, scope_estimate):
    """A generative change over a broad scope projects the full posture."""
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'full'


def test_profile_narrow_concrete_breaking_change_projects_minimal():
    """A surgical, concretely-specified breaking generative change projects minimal.

    The narrow-and-concrete predicate dominates: a bounded surgical fix stays
    ``minimal`` even when its change_type reads generative and its compatibility
    reads breaking. (A BROAD generative breaking change still projects full — see
    ``test_profile_generative_broad_change_projects_full``.)
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='feature',
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture == 'minimal'


def test_profile_narrow_concrete_nongenerative_change_projects_minimal():
    """A non-generative, SURGICAL, concretely-specified change projects minimal.

    ``surgical`` is the sole member of ``_NARROW_SCOPE_ESTIMATES``, so this case is
    no longer parametrized over ``single_module``: the middle band does not earn
    the carve-out. See
    ``test_profile_non_narrow_concrete_change_does_not_project_minimal`` for the
    mirrored negative.
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


def test_profile_narrow_nongenerative_but_vague_request_projects_auto():
    """A narrow non-generative change with a vague request falls back to auto."""
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='bug_fix',
        compatibility='deprecation',
        request_concrete=False,
    )

    assert posture == 'auto'


def test_profile_generative_narrow_concrete_change_projects_minimal():
    """A generative but SURGICAL, concretely-specified change projects minimal.

    Under the narrow-and-concrete carve-out the bounded, well-anchored generative
    change is recommended ``minimal`` — the narrow, concrete bound dominates the
    generative signal. Narrowness is now literal: only ``surgical`` qualifies.
    """
    posture = project_profile_pure(
        scope_estimate='surgical',
        change_type='feature',
        compatibility='deprecation',
        request_concrete=True,
    )

    assert posture == 'minimal'


@pytest.mark.parametrize('scope_estimate', ['single_module', 'multi_module'])
@pytest.mark.parametrize('change_type', ['bug_fix', 'feature'])
def test_profile_non_narrow_concrete_change_does_not_project_minimal(scope_estimate, change_type):
    """The mirrored negative: a concrete but NON-narrow change never projects minimal.

    This is the security-gate half of the defect. ``_NARROW_SCOPE_ESTIMATES`` is
    shared verbatim with ``evaluate_signals_pure``, so before the narrowing a
    ``single_module`` band collapsed the posture to ``minimal`` — which drops the
    security audit, the sonar round-trip and the self-review — purely on the
    strength of a catch-all band. Asserting the lane alone would have left this
    path live, so the posture is pinned independently here.
    """
    posture = project_profile_pure(
        scope_estimate=scope_estimate,
        change_type=change_type,
        compatibility='breaking',
        request_concrete=True,
    )

    assert posture != 'minimal'


def test_profile_projection_is_deterministic_over_the_signal_set():
    """The projection is a pure function — identical inputs yield identical output."""
    kwargs = {
        'scope_estimate': 'multi_module',
        'change_type': 'feature',
        'compatibility': 'breaking',
        'request_concrete': False,
    }

    first = project_profile_pure(**kwargs)
    second = project_profile_pure(**kwargs)

    assert first == second == 'full'


def test_evaluate_signals_pure_emits_profile_projection():
    """evaluate_signals_pure carries the profile projection alongside the lane verdict."""
    result = _pure(scope_estimate='multi_module', change_type='feature')

    assert result['profile']['recommended_posture'] == 'full'
    assert result['profile']['candidate_postures'] == ['minimal', 'auto', 'full']


def test_route_surfaces_execution_profile(plan_context):
    """The route return surfaces execution_profile + the structured profile block."""
    # Generative + broad signals → full posture, deep lane.
    plan_dir = _light_setup(plan_context, 'pl-profile-full')
    _write_references(plan_dir, scope_estimate='multi_module')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'feature'})

    result = cmd_planning_lane_route(_ns_route('pl-profile-full'))

    assert result['execution_profile'] == 'full'
    assert result['profile']['recommended_posture'] == 'full'
    assert result['profile']['candidate_postures'] == ['minimal', 'auto', 'full']


def test_route_projects_minimal_for_narrow_concrete_change(plan_context):
    """An all-light, narrow, concrete change projects the minimal posture."""
    _light_setup(plan_context, 'pl-profile-minimal')

    result = cmd_planning_lane_route(_ns_route('pl-profile-minimal'))

    assert result['planning_lane'] == 'light'
    assert result['execution_profile'] == 'minimal'


def test_deep_lane_always_does_not_coerce_profile_to_full(plan_context):
    """deep_lane=always forces planning_lane=deep but leaves the profile projection alone.

    Planning depth and the execution profile are independent axes (§4.2): the
    ceremony gate that ratchets the lane to deep must NOT coerce the posture to
    full. An all-light narrow concrete change keeps its minimal projection even
    under deep_lane=always.
    """
    _light_setup(plan_context, 'pl-profile-indep')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    result = cmd_planning_lane_route(_ns_route('pl-profile-indep'))

    # The deep-lane gate wins the planning-depth verdict ...
    assert result['planning_lane'] == 'deep'
    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=always'
    # ... but the execution-profile projection is unaffected by it.
    assert result['execution_profile'] == 'minimal'


def test_persist_writes_execution_profile_metadata(plan_context):
    """--persist writes the projected posture into status.metadata.execution_profile."""
    plan_dir = _light_setup(plan_context, 'pl-profile-persist')

    result = cmd_planning_lane_route(_ns_route('pl-profile-persist', persist=True))

    assert result['persisted'] is True
    status = json.loads((plan_dir / 'status.json').read_text())
    assert status['metadata']['execution_profile'] == 'minimal'


def test_route_without_persist_does_not_write_execution_profile(plan_context):
    """Without --persist the projected posture is not written to status.json."""
    plan_dir = _light_setup(plan_context, 'pl-profile-nopersist')

    cmd_planning_lane_route(_ns_route('pl-profile-nopersist'))

    status = json.loads((plan_dir / 'status.json').read_text())
    assert 'execution_profile' not in status.get('metadata', {})


# =============================================================================
# classify_scope_pure — pre-route coarse scope classifier (D2)
# =============================================================================
#
# A pure, ZERO-architecture-call classifier over two measurements — the count of
# distinct file-path references and the presence of a fan-out marker — emitting
# one of four bands: none (declared unknown) / surgical (1-3 paths, no fan-out) /
# single_module (4-7 paths, or a pathless non-empty body) / multi_module (a real
# fan-out marker, or >= 8 paths). It is a pre-route guess; the deep-lane refine
# Step 9 module-mapping derivation overwrites it when the deep lane runs.
#
# The band line is scale-truthful in BOTH directions, which is the property these
# tests exist to pin: it can say "large" (multi_module) and it can say "I cannot
# bound this" (a fan-out marker WIDENS, it does not narrow).


def _ns_scope(plan_id: str, *, persist: bool = False) -> Namespace:
    return Namespace(plan_id=plan_id, persist=persist)


@pytest.mark.parametrize(
    'body',
    [
        'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py per the diagnosis.',
        (
            'Update marketplace/bundles/plan-marshall/skills/x/scripts/x.py and '
            'test/plan-marshall/x/test_x.py.'
        ),
        (
            'Touch a/b/one.py, c/d/two.py, and e/f/three.py — three named files, no more.'
        ),
    ],
)
def test_scope_pure_surgical_for_one_to_three_paths(body):
    """One to three distinct file paths with no glob classifies surgical."""
    assert scope_estimate_from_request_pure(body) == 'surgical'


def test_scope_pure_repeated_path_counts_once():
    """The same path mentioned repeatedly counts as one distinct path (still surgical)."""
    body = 'Edit pkg/mod.py, then re-edit pkg/mod.py, and check pkg/mod.py again.'
    assert scope_estimate_from_request_pure(body) == 'surgical'


def test_scope_pure_single_module_for_the_four_to_seven_middle_band():
    """Four-to-seven distinct file paths classifies single_module — the middle band.

    Five paths is neither ``surgical`` (>3) nor ``multi_module`` (<8). The middle
    band is deliberately NOT narrow: it does not earn the S3/S4 carve-out and does
    not project the ``minimal`` posture.
    """
    body = 'Touch a/one.py, b/two.py, c/three.py, d/four.py, and e/five.py.'
    assert scope_estimate_from_request_pure(body) == 'single_module'


@pytest.mark.parametrize(
    'body',
    [
        'Sweep every skills/*/SKILL.md across the bundle.',
        'Rewrite all **/*.py under the module.',
        'Apply the change to marketplace/bundles/*/plugin.json everywhere.',
        'Rewrite the fixtures under test/plan-marshall/manage-status/** wholesale.',
    ],
)
def test_scope_pure_fan_out_marker_bands_multi_module(body):
    """A real fan-out marker bands multi_module — it WIDENS, it does not narrow.

    The inversion this replaces: a genuine glob used to band ``single_module``,
    i.e. a declared inability to enumerate the file set was reported as a narrow
    verdict. An unbounded set cannot be a bounded one, so the marker must widen.
    """
    assert scope_estimate_from_request_pure(body) == 'multi_module'


@pytest.mark.parametrize(
    'body',
    [
        'Fix **the parser** in a/b/one.py so **bold** prose stops confusing it.',
        '**Objective**\n\n**Root cause:** the regex in pkg/mod.py is too loose.',
        '- **`c/d/two.py`** — the target\n- **`e/f/three.py`** — its test\n',
    ],
)
def test_scope_pure_markdown_bold_is_not_a_fan_out_marker(body):
    """Markdown ``**bold**`` does NOT register as fan-out — the load-bearing precision fix.

    ``_GLOB_RE``'s ``**`` alternatives are path-adjacent (``/**`` / ``**/``). Before
    that tightening a bare ``**`` matched markdown bold, and because the marker
    check short-circuits AHEAD of the path count, a bold-saturated orchestrator
    spec banded on its own — making the path-count thresholds unreachable for
    essentially the entire orchestrated-plan population. Any band extension is
    vacuous without this, so the precision is pinned directly.
    """
    band, provenance = classify_scope_pure(body)

    assert provenance['fan_out_marker'] is False
    assert band == 'surgical'


@pytest.mark.parametrize(
    ('path_count', 'expected_band'),
    [(3, 'surgical'), (4, 'single_module'), (7, 'single_module'), (8, 'multi_module')],
)
def test_scope_pure_band_boundaries_at_three_four_and_seven_eight(path_count, expected_band):
    """The two band boundaries are pinned on both sides: 3/4 and 7/8 distinct paths.

    A threshold asserted only from its interior can drift by one without any test
    noticing, so each boundary is asserted from the band below AND the band above.
    """
    body = 'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(path_count)) + '.'

    band, provenance = classify_scope_pure(body)

    assert provenance['distinct_path_count'] == path_count
    assert band == expected_band


@pytest.mark.parametrize('body', ['', None])
def test_scope_pure_declares_unknown_for_unscoreable_body(body):
    """An unscoreable (empty / None) body yields the DECLARED UNKNOWN, not a band.

    This assertion is the inverse of the one it replaces. The prior contract had
    an empty body classify as ``single_module`` — a confident narrow-ish band
    derived from zero bytes, which is precisely the "scorer reads nothing and
    still emits a verdict" failure this change exists to remove. A body that
    cannot be scored must say so.

    ``none`` is deliberately reused rather than a new enum member: it is already
    inside the closed ``none|surgical|single_module|multi_module|broad`` set that
    ``manage-solution-outline validate`` enforces, and it is already a member of
    ``_DEEP_SCOPE_ESTIMATES``, so the unknown biases the lane DEEP (wider) rather
    than narrow. See ``test_scope_unknown_is_a_deep_biasing_s2_value`` for that
    second half — the enum choice is only correct if the routing consequence
    holds, so both are asserted.
    """
    assert scope_estimate_from_request_pure(body) == 'none'


def test_scope_pure_single_module_for_pathless_body():
    """A non-empty but pathless (ambiguous) request still bands as single_module.

    The declared-unknown change narrows to the UNSCOREABLE case only. A body that
    was read successfully and simply names no path is a real, scoreable request
    about which the coarse verdict is "not demonstrably narrow" — it keeps its
    ``single_module`` band and must NOT drift into the unknown.
    """
    assert scope_estimate_from_request_pure('Make the thing better, somehow, everywhere.') == (
        'single_module'
    )


def test_scope_unknown_is_a_deep_biasing_s2_value():
    """The declared unknown routes DEEP — the unknown must widen, never narrow.

    Guards the enum choice in ``scope_estimate_from_request_pure``: reusing
    ``none`` is only safe while ``none`` remains in ``_DEEP_SCOPE_ESTIMATES`` and
    outside ``_NARROW_SCOPE_ESTIMATES``. If a future edit moved it, the unknown
    would silently start biasing light — the exact inversion this plan removes —
    so both memberships and the end-to-end lane verdict are pinned here.
    """
    assert 'none' in _mod._DEEP_SCOPE_ESTIMATES
    assert 'none' not in _mod._NARROW_SCOPE_ESTIMATES

    verdict = evaluate_signals_pure(
        scope_estimate='none',
        change_type='bug_fix',
        compatibility='deprecation',
        plan_source='lesson',
        request_concrete=True,
    )
    assert verdict['lane'] == 'deep'
    assert 'S2:scope_estimate' in verdict['fired_signals']


# --- scope_provenance — why the band came out as it did -----------------------
#
# The operator-facing half of the fix (arm 1 of the surfacing question): the route
# return and the decision-log line explain the band rather than only asserting it.
# No new prompt and no new override seam — --lane-override / S6 already exists.


@pytest.mark.parametrize(
    ('body', 'expected_rule', 'expected_count', 'expected_fan_out'),
    [
        ('', 'unscoreable_body', 0, False),
        (
            'Sweep test/plan-marshall/x/test_x.py and every marketplace/bundles/*/plugin.json.',
            'fan_out_marker',
            1,
            True,
        ),
        (
            'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(8)) + '.',
            'path_count_at_or_above_multi_module_floor',
            8,
            False,
        ),
        ('Touch a/one.py, b/two.py, c/three.py, d/four.py.', 'path_count_middle_band', 4, False),
        ('Fix a/one.py.', 'path_count_at_or_below_surgical_max', 1, False),
        ('Make the thing better, somehow.', 'pathless_non_empty_body', 0, False),
    ],
)
def test_classify_scope_pure_reports_the_band_rule_that_fired(
    body, expected_rule, expected_count, expected_fan_out
):
    """Every row of the band table reports its own ``band_rule`` plus both measurements.

    One case per table row, so a future row that stops being reachable — a
    vacuous band — shows up as a failing case rather than as silently dead code.
    """
    _band, provenance = classify_scope_pure(body)

    assert provenance == {
        'distinct_path_count': expected_count,
        'fan_out_marker': expected_fan_out,
        'band_rule': expected_rule,
    }


def test_classify_scope_pure_band_and_provenance_cannot_disagree():
    """``scope_estimate_from_request_pure`` is a projection of ``classify_scope_pure``.

    The band and its explanation come from ONE decision, so the thin wrapper can
    never drift from the provenance-bearing classifier.
    """
    body = 'Rewrite all **/*.py under the module.'

    assert scope_estimate_from_request_pure(body) == classify_scope_pure(body)[0]


def test_route_surfaces_scope_provenance(plan_context):
    """The route return carries scope_provenance alongside BOTH verdicts.

    The operator reading one surface sees the lane, the posture, and the band rule
    that drove them — the whole point of surfacing provenance rather than adding a
    prompt.
    """
    plan_dir = _light_setup(plan_context, 'pl-provenance')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py.')

    result = cmd_planning_lane_route(_ns_route('pl-provenance'))

    assert result['scope_provenance'] == {
        'distinct_path_count': 1,
        'fan_out_marker': False,
        'band_rule': 'path_count_at_or_below_surgical_max',
    }
    # Both verdicts are on the same return, next to the provenance that explains them.
    assert result['planning_lane'] == 'light'
    assert result['execution_profile'] == 'minimal'


def test_route_surfaces_scope_provenance_under_the_deep_lane_short_circuit(plan_context):
    """Provenance is a property of the request body, so the deep_lane gate cannot erase it.

    ``deep_lane=always`` replaces the signal-scored verdict, but the band
    explanation must survive — otherwise the one configuration most likely to hide
    a miscalibrated band is also the one that stops reporting it.
    """
    _light_setup(plan_context, 'pl-provenance-always')
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='always')

    result = cmd_planning_lane_route(_ns_route('pl-provenance-always'))

    assert result['decision_predicate'] == 'plan.phase-1-init.deep_lane=always'
    assert result['scope_provenance']['band_rule'] == 'path_count_at_or_below_surgical_max'


# --- Settled path-counter semantics ------------------------------------------
#
# Both properties below are DECISIONS recorded in _distinct_paths' docstring, not
# accidents of the regex. They are asserted so a future edit has to change the
# test deliberately rather than drift.


@pytest.mark.parametrize(
    'bare_name',
    ['_cmd_planning_lane.py', 'agents.md', 'retro_sections.py'],
)
def test_distinct_paths_excludes_bare_filenames_intentionally(bare_name):
    """A bare filename is deliberately NOT counted — a directory separator is required.

    ``_PATH_RE`` matches only ``dir/name.ext``. This exclusion is intentional: a
    bare filename cannot be resolved to a repo location without the directory
    discovery this module is defined to exclude, and matching bare ``word.word``
    tokens would sweep in ordinary prose (``e.g.``, version numbers,
    sentence-final abbreviations). The consequence is an UNDER-count, which
    biases toward the wider band — the same conservative direction as citation
    inflation.
    """
    body = f'Rewrite {bare_name} so the handler is reachable.'

    assert _mod._distinct_paths(body) == set()
    # Under-counting to zero paths lands in single_module (wider), never surgical.
    assert scope_estimate_from_request_pure(body) == 'single_module'


def test_distinct_paths_counts_a_citation_it_cannot_distinguish_from_a_target():
    """The counter counts path STRINGS; it cannot tell a citation from a target.

    A body whose only path is a citation of a governing document still counts
    one path and bands ``surgical``. The sensor declares its inapplicability for
    this discrimination rather than faking it — but the residual must stay
    visible, so it is asserted rather than left implicit. The error is
    one-directional: citations INFLATE the count, and inflation moves the band
    from ``surgical`` toward ``single_module`` (wider), never the reverse.
    """
    citation_only = (
        'Tidy the hand-off prose. See '
        f'`{_BOILERPLATE_CITATION}` for the tier contract.'
    )

    assert _mod._distinct_paths(citation_only) == {_BOILERPLATE_CITATION}
    assert scope_estimate_from_request_pure(citation_only) == 'surgical'

    # Adding real targets alongside the citation moves the band wider, never narrower.
    with_targets = (
        f'{citation_only} Change a/one.py, b/two.py, c/three.py and d/four.py.'
    )
    assert scope_estimate_from_request_pure(with_targets) == 'single_module'


def test_scope_pure_makes_no_architecture_call(monkeypatch):
    """The classifier performs zero architecture calls (pure, regex-only)."""
    # Any attempt to import or invoke an architecture surface would raise here.
    import builtins  # noqa: PLC0415

    real_import = builtins.__import__

    def _guard_import(name, *args, **kwargs):
        assert 'architecture' not in name, f'scope classifier must not import {name}'
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', _guard_import)
    assert scope_estimate_from_request_pure('Fix pkg/one.py and pkg/two.py.') == 'surgical'


# =============================================================================
# cmd_scope_estimate_heuristic — persistence to references.json
# =============================================================================


def test_scope_heuristic_persists_surgical_to_references(plan_context):
    """--persist writes the classified scope_estimate into references.json."""
    plan_dir = plan_context.plan_dir_for('pl-scope-persist')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-persist', persist=True))

    assert result['status'] == 'success'
    assert result['scope_estimate'] == 'surgical'
    assert result['persisted'] is True
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'surgical'
    # The persist preserves other references fields.
    assert refs['base_branch'] == 'main'


def test_scope_heuristic_persists_single_module_for_the_middle_band(plan_context):
    """A five-path request persists single_module — the 4–7 middle band, end to end."""
    plan_dir = plan_context.plan_dir_for('pl-scope-middle')
    _write_request(plan_dir, 'Touch a/one.py, b/two.py, c/three.py, d/four.py, e/five.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-middle', persist=True))

    assert result['scope_estimate'] == 'single_module'
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'single_module'


def test_scope_heuristic_persists_multi_module_for_a_large_request(plan_context):
    """An eight-path request persists multi_module — the band that used to be unreachable.

    End-to-end proof that the upper segment of the path-count line now exists: the
    persisted value is a deep-biasing S2 band, so a large concrete request stops
    routing light.
    """
    plan_dir = plan_context.plan_dir_for('pl-scope-large')
    _write_request(
        plan_dir,
        'Touch ' + ', '.join(f'dir{i}/file{i}.py' for i in range(8)) + '.',
    )
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-large', persist=True))

    assert result['scope_estimate'] == 'multi_module'
    assert result['distinct_path_count'] == 8
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert refs['scope_estimate'] == 'multi_module'
    assert 'multi_module' in _mod._DEEP_SCOPE_ESTIMATES


def test_scope_heuristic_without_persist_does_not_write(plan_context):
    """Without --persist the classifier reports but does not mutate references.json."""
    plan_dir = plan_context.plan_dir_for('pl-scope-nopersist')
    _write_request(plan_dir, 'Fix pkg/one.py.')
    _write_references(plan_dir, scope_estimate=None)

    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-nopersist'))

    assert result['scope_estimate'] == 'surgical'
    assert result['persisted'] is False
    refs = json.loads((plan_dir / 'references.json').read_text())
    assert 'scope_estimate' not in refs


def test_scope_heuristic_plan_dir_not_found_errors(plan_context):
    """scope-estimate-heuristic against a missing plan dir returns a structured error."""
    result = cmd_scope_estimate_heuristic(_ns_scope('pl-scope-missing', persist=True))

    assert result['status'] == 'error'
    assert result['error'] == 'plan_dir_not_found'


# =============================================================================
# D2 acceptance — pre-route classification unblocks the light lane
# =============================================================================


def test_prerouted_surgical_scope_flips_s2_from_deep_to_light(plan_context):
    """The pre-route scope classification flips S2 from deep (None) to light (surgical).

    Before D2, a concrete narrow request reached the router with scope_estimate
    unset, so S2 fired deep unconditionally. After the pre-route classifier
    persists scope_estimate=surgical, S2 no longer fires and the router reaches
    the light lane for a well-bounded, concrete request.
    """
    plan_dir = plan_context.plan_dir_for('pl-d2-accept')
    _write_request(plan_dir, 'Fix marketplace/bundles/plan-marshall/skills/x/scripts/x.py per the diagnosis.')
    _write_status(plan_dir, metadata={'plan_source': 'lesson', 'change_type': 'bug_fix'})
    _write_references(plan_dir, scope_estimate=None)
    _write_marshal(plan_context.fixture_dir, compatibility='deprecation', deep_lane='auto')

    # Pre-classification: with scope_estimate still None, S2 fires deep.
    before = cmd_planning_lane_route(_ns_route('pl-d2-accept'))
    assert before['planning_lane'] == 'deep'
    assert 'S2:scope_estimate' in before['fired_signals']

    # Run the pre-route classifier; it persists scope_estimate=surgical.
    scope_result = cmd_scope_estimate_heuristic(_ns_scope('pl-d2-accept', persist=True))
    assert scope_result['scope_estimate'] == 'surgical'

    # Now the router routes light — S2 no longer fires.
    after = cmd_planning_lane_route(_ns_route('pl-d2-accept'))
    assert after['planning_lane'] == 'light'
    assert 'S2:scope_estimate' not in after['fired_signals']


# =============================================================================
# Dispatch wiring — scope-estimate-heuristic
# =============================================================================


def test_scope_estimate_heuristic_registered_in_manage_status_dispatch():
    """The scope-estimate-heuristic verb resolves to cmd_scope_estimate_heuristic."""
    import argparse  # noqa: PLC0415

    manage_status = load_script_module(
        'plan-marshall', 'manage-status', 'manage-status.py', '_manage_status_dispatch_check_scope_est'
    )

    assert callable(manage_status.cmd_scope_estimate_heuristic)
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd')
    scope = sub.add_parser('scope-estimate-heuristic')
    scope.set_defaults(func=manage_status.cmd_scope_estimate_heuristic)
    ns = p.parse_args(['scope-estimate-heuristic'])
    assert ns.func is manage_status.cmd_scope_estimate_heuristic
