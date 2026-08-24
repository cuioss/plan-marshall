#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The binding between the completion marker's PRODUCER and CONSUMER shapes.

``_step_completion_marker`` (`script-shared/scripts/_step_completion_marker.py`)
holds two separately-authored literals: :data:`COMPLETION_MARKER_TEMPLATE`, which
``manage-status mark-step-done`` formats the emitted work-log line from, and
:data:`COMPLETION_MARKER_RE`, which ``plan-retrospective``'s dispatch audit reads
that line back with. They live in one module, but co-location is not coupling —
nothing in the module makes an edit to one shape fail because of the other.

This file IS that coupling. It round-trips the pair: format a line with the
template, then require the pattern to recover the same ``step`` and ``outcome``
from it. A widening or renaming edit that leaves the consumer matching a shape
that is no longer written fails here, rather than passing every suite green and
silently under-counting D3's ``completion_count`` denominator in production.

The negative controls below are the matched half: each mutates the template into
a realistic drifted shape and asserts the round-trip FAILS. Without them, a
round-trip assertion that could never go red would prove only that the current
pair happens to agree, not that the guard bites.
"""

import re

import pytest

# script-shared/scripts is injected onto PYTHONPATH by the test conftest, so the
# shared module imports by bare name — the same pattern test_step_key_canonical
# uses for the sibling _step_key_canonical resolver.
from _step_completion_marker import (
    COMPLETION_MARKER_RE,
    COMPLETION_MARKER_TEMPLATE,
    format_completion_marker,
)

#: The terminal outcomes ``mark-step-done`` validates against and emits. Kept in
#: sync with ``_cmd_mark_step.VALID_OUTCOMES`` by the parity test below rather
#: than by hope — a new outcome whose spelling the read pattern's
#: ``[A-Za-z_]+`` class cannot express must fail here, not in a retrospective.
_VALID_OUTCOMES = ('done', 'skipped', 'loop_back', 'failed')

#: Step-key shapes the marker legitimately carries, spanning every prefix form
#: ``canonicalize_step_key`` preserves: bare, ``default:``, a colon-nested verify
#: sub-key, ``project:``, and an opt-in ``bundle:skill`` id.
_STEP_KEYS = (
    'push',
    'default:push',
    'verify:quality-gate',
    'project:finalize-step-plugin-doctor',
    'plan-marshall:plan-retrospective',
)

_PHASE = '6-finalize'


@pytest.mark.parametrize('outcome', _VALID_OUTCOMES)
@pytest.mark.parametrize('step', _STEP_KEYS)
def test_read_pattern_round_trips_every_emitted_line(step: str, outcome: str):
    """The consumer recovers step and outcome from what the producer formats."""
    # Arrange — the exact line the producer writes to the work log.
    line = format_completion_marker(phase=_PHASE, step=step, outcome=outcome)

    # Act — the exact pattern the dispatch audit reads it back with.
    match = COMPLETION_MARKER_RE.search(line)

    # Assert — the pair agrees on the shape AND on both captured fields.
    assert match is not None, (
        f'COMPLETION_MARKER_RE does not match a line COMPLETION_MARKER_TEMPLATE '
        f'produced: {line!r}. The producer and consumer shapes have drifted.'
    )
    assert match.group('step') == step, (
        f'Round-tripped step {match.group("step")!r} != emitted {step!r} in {line!r}.'
    )
    assert match.group('outcome') == outcome, (
        f'Round-tripped outcome {match.group("outcome")!r} != emitted {outcome!r} '
        f'in {line!r}.'
    )


def test_valid_outcomes_match_the_producers_enumeration():
    """The outcome set exercised above IS the producer's, not a stale copy.

    A population-derived check: the parametrization is only meaningful if it
    covers every outcome ``mark-step-done`` can actually emit.
    """
    from conftest import load_script_module

    mark_step = load_script_module(
        'plan-marshall', 'manage-status', '_cmd_mark_step.py', '_completion_marker_producer'
    )

    assert set(_VALID_OUTCOMES) == set(mark_step.VALID_OUTCOMES), (
        f'This file round-trips {sorted(_VALID_OUTCOMES)} but the producer emits '
        f'{sorted(mark_step.VALID_OUTCOMES)}. An outcome absent here is an outcome '
        f'whose round-trip nothing checks.'
    )


@pytest.mark.parametrize('step', _STEP_KEYS)
def test_read_pattern_still_reads_a_historical_line_carrying_no_outcome(step: str):
    """The ``(outcome=…)`` suffix is deliberately OPTIONAL to the consumer.

    A retrospective reads work logs written by earlier runs, whose completion
    lines predate the outcome suffix. Anchoring the pattern to require it would
    drop every historical completion from ``completion_count`` and grade the D3
    ratio against a zero denominator. Pinned here so a future tightening of the
    regex — the obvious "fix" once the template always emits the suffix — cannot
    land silently.
    """
    # Arrange — derive the pre-widening shape FROM the template rather than
    # hand-typing it, so this control cannot itself drift from the real line.
    historical = COMPLETION_MARKER_TEMPLATE.split(' (outcome=')[0].format(
        phase=_PHASE, step=step
    )

    match = COMPLETION_MARKER_RE.search(historical)

    assert match is not None, f'Historical completion line no longer matches: {historical!r}'
    assert match.group('step') == step
    assert match.group('outcome') is None


#: Matched negative controls — realistic drifted templates whose round-trip MUST
#: fail. Each names the class of edit it stands in for.
_DRIFTED_TEMPLATES = (
    pytest.param(
        '[STEP] (plan-marshall:phase-{phase}) Finished step: {step} (outcome={outcome})',
        'the marker phrase was renamed',
        id='phrase-renamed',
    ),
    pytest.param(
        '[STEP] (plan-marshall:phase-{phase}) Completed step: [{step}] (outcome={outcome})',
        'the step key was wrapped in delimiters',
        id='step-wrapped',
    ),
    pytest.param(
        '[STEP] (plan-marshall:phase-{phase}) Completed step: (outcome={outcome}) {step}',
        'the outcome suffix moved ahead of the step key',
        id='fields-reordered',
    ),
    pytest.param(
        '[STEP] (plan-marshall:phase-{phase}) Completed step: {step} (result={outcome})',
        'the outcome key was renamed',
        id='outcome-key-renamed',
    ),
    pytest.param(
        '[PHASE-STEP] (plan-marshall:phase-{phase}) Completed step: {step} (outcome={outcome})',
        'the log-category bracket was renamed',
        id='bracket-renamed',
    ),
)


@pytest.mark.parametrize('drifted_template, drift', _DRIFTED_TEMPLATES)
def test_round_trip_fails_when_the_emitted_shape_drifts(drifted_template: str, drift: str):
    """The guard bites: a drifted producer shape does NOT round-trip.

    This is the control for every positive assertion above. If a mutation of the
    template could still round-trip, the round-trip test would be vacuous — green
    whether or not the two literals agree.
    """
    line = drifted_template.format(phase=_PHASE, step='push', outcome='done')

    match = COMPLETION_MARKER_RE.search(line)
    round_tripped = (
        match is not None
        and match.group('step') == 'push'
        and match.group('outcome') == 'done'
    )

    assert not round_tripped, (
        f'COMPLETION_MARKER_RE round-tripped a drifted line ({drift}): {line!r}. '
        f'The round-trip guard cannot detect this class of producer/consumer drift.'
    )


def test_drift_controls_are_genuine_mutations_of_the_live_template():
    """Every control differs from the shipped template — no accidental no-ops.

    A control that is byte-identical to the real template would assert that the
    real pair fails to round-trip, inverting the guard. Cheap to check, and it
    keeps the control set honest if the template is edited later.
    """
    for param in _DRIFTED_TEMPLATES:
        drifted = param.values[0]
        assert drifted != COMPLETION_MARKER_TEMPLATE, (
            f'Drift control {param.id!r} is identical to the live template.'
        )


def test_read_pattern_ignores_a_non_completion_step_line():
    """A ``[STEP]`` line that is not a completion marker is not counted.

    ``completion_count`` is a count of completions; a dispatch-or-progress
    ``[STEP]`` line matching it would inflate the D3 denominator.
    """
    assert COMPLETION_MARKER_RE.search('[STEP] (plan-marshall:phase-6-finalize) Starting step: push') is None


def test_template_and_pattern_agree_on_the_phase_the_producer_scopes_to():
    """The emitted line names the phase, and the pattern tolerates any phase.

    The producer scopes emission to ``6-finalize``; the consumer must not hard-code
    that, because a widening of the emitting phase set would otherwise need a
    second, easily-missed edit on the read side.
    """
    line = format_completion_marker(phase='5-execute', step='push', outcome='done')
    match = COMPLETION_MARKER_RE.search(line)

    assert match is not None, 'The read pattern must not be pinned to one phase key.'
    assert match.group('step') == 'push'


def test_read_pattern_is_the_compiled_form_the_consumer_imports():
    """Sanity: the exported pattern is a compiled regex, not a raw string."""
    assert isinstance(COMPLETION_MARKER_RE, re.Pattern)
