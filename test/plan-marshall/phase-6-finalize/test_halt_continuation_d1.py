#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Derivation guard for the halt-continuation contract (PLAN-LB-53 D1).

A recorded halt used to be a decision nobody could read back: the main context
recorded ``failed``, logged "halted", and then improvised a recovery the workflow
does not name — ``tools.opencode.session_move`` on OpenCode, followed by a retry.
This module pins the two mechanisms that replace that improvisation:

(1) **The halt is persisted and the continuation is decided against it.** The
    named set is CLOSED and mirrors the roster declared in
    ``phase-6-finalize/SKILL.md`` § "Halt continuation roster";
    :func:`test_the_declared_roster_matches_the_script` cross-checks the document
    against the script's own ``NAMED_CONTINUATIONS``, so the two cannot drift.
(2) **A resolution over an unanswered escalation is refused at the write
    boundary** — ``mark-step-done --outcome done|skipped`` returns
    ``escalation_unanswered`` and writes nothing until ``halt answer`` records the
    option the operator selected.

The Done-when clauses this file is the evidence for are named in each test's
docstring; every one of them drives the real handler, never a mock of it.

Two falsifiability notes, so a green run is read for what it is: the refusal
tests exercise the handler as it exists, and the roster-parity test fails if
either side is edited alone. No test here asserts a behaviour the pre-change tree
already had — before this change ``mark-step-done`` had no escalation read at all
and there was no continuation seam, so every assertion below is new surface.
"""

from __future__ import annotations

import re
from argparse import Namespace
from pathlib import Path
from typing import Any, cast

import pytest

from conftest import MARKETPLACE_ROOT, load_script_module

_halt = load_script_module('plan-marshall', 'manage-status', '_cmd_halt.py', '_d1_halt_cmd')
_mark_step = load_script_module('plan-marshall', 'manage-status', '_cmd_mark_step.py', '_d1_mark_step')
_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_d1_lifecycle')
_status_core = load_script_module('plan-marshall', 'manage-status', '_status_core.py', '_d1_status_core')
_continuation = load_script_module('plan-marshall', 'phase-6-finalize', 'halt_continuation.py', '_d1_halt_continuation')
_handshake = load_script_module('plan-marshall', 'plan-marshall', '_handshake_commands.py', '_d1_handshake')
_handshake_store = load_script_module('plan-marshall', 'plan-marshall', '_handshake_store.py', '_d1_handshake_store')

cmd_create = _lifecycle.cmd_create
cmd_mark_step_done = _mark_step.cmd_mark_step_done
read_status = _status_core.read_status
cmd_halt_record = _halt.cmd_halt_record
cmd_halt_answer = _halt.cmd_halt_answer
cmd_halt_read = _halt.cmd_halt_read
cmd_capture = _handshake.cmd_capture

_PHASE = '6-finalize'
_STEP = 'create-pr'

#: The dispatcher document that declares the roster this script mirrors.
_DISPATCHER_DOC: Path = MARKETPLACE_ROOT / 'plan-marshall' / 'skills' / 'phase-6-finalize' / 'SKILL.md'

#: One roster row: ``| `token` | what it is | bound |``.
_ROSTER_ROW_RE = re.compile(r'^\|\s*`(?P<token>[a-z_]+)`\s*\|', re.MULTILINE)


def _make_plan(plan_id: str) -> None:
    cmd_create(
        Namespace(
            plan_id=plan_id,
            title='Halt Continuation Guard',
            phases='1-init,2-refine,3-outline,4-plan,5-execute,6-finalize',
            force=False,
        )
    )


def _record(plan_id: str, *, escalate: bool = False, step: str = _STEP, outcome: str = 'failed') -> dict[str, Any]:
    return cast(
        dict[str, Any],
        cmd_halt_record(
            Namespace(
                plan_id=plan_id,
                phase=_PHASE,
                step=step,
                outcome=outcome,
                reason='post-dispatch guard: step returned without a terminal record',
                escalate_ask=escalate,
                option=['Wait another 600s', 'Defer merge'] if escalate else None,
            )
        ),
    )


def _mark(plan_id: str, outcome: str, *, step: str = _STEP, loop_back_target: str | None = None) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        cmd_mark_step_done(
            Namespace(
                plan_id=plan_id,
                phase=_PHASE,
                step=step,
                outcome=outcome,
                force=False,
                display_detail='recorded by the halt-continuation guard test',
                head_at_completion=None,
                loop_back_target=loop_back_target,
                fact=None,
            )
        ),
    )


def _check(
    plan_id: str, continuation: str, *, attempt: int | None = None, max_attempts: int | None = None
) -> dict[str, Any]:
    return cast(
        dict[str, Any],
        _continuation.check_continuation(
            plan_id=plan_id,
            phase=_PHASE,
            step=_STEP,
            continuation=continuation,
            attempt=attempt,
            max_attempts=max_attempts,
        ),
    )


# ---------------------------------------------------------------------------
# Done when: a halted step refuses a re-run that is not a named continuation
# ---------------------------------------------------------------------------


def test_a_halted_step_refuses_a_re_run_that_is_not_a_named_continuation(plan_context):
    """A recorded halt + an unnamed continuation (``session_move``) reads a refusal.

    Done-when clause: *"a test records a halted create-pr step and reads a refusal
    for a re-run that is not a named continuation"*.
    """
    plan_id = 'halt-refusal'
    _make_plan(plan_id)
    _record(plan_id)

    result = _check(plan_id, 'session_move')

    assert result['status'] == 'error'
    assert result['error'] == 'halt_continuation_refused'
    assert result['allowed'] is False
    assert result['halted'] is True
    assert sorted(result['allowed_continuations']) == ['loop_back', 'operator_question', 'retry']
    # The refusal NAMES the named continuations, so the caller is pointed at a
    # real way forward rather than merely told "no".
    for token in ('retry', 'loop_back', 'operator_question'):
        assert token in result['message'], f'the refusal does not name {token!r}: {result["message"]}'
    assert 'session_move' in result['message']


@pytest.mark.parametrize(
    'continuation,kwargs',
    [
        ('loop_back', {}),
        ('operator_question', {}),
        ('retry', {'attempt': 1, 'max_attempts': 1}),
    ],
)
def test_a_named_continuation_passes(plan_context, continuation, kwargs):
    """Every named continuation is admitted for a plain (non-escalated) halt.

    Done-when clause: *"a named continuation passes"*.
    """
    plan_id = f'halt-named-{continuation.replace("_", "-")}'
    _make_plan(plan_id)
    _record(plan_id)

    result = _check(plan_id, continuation, **kwargs)

    assert result['status'] == 'success', result
    assert result['allowed'] is True
    assert result['continuation'] == continuation
    assert result['halted'] is True


def test_a_step_with_no_halt_record_admits_every_continuation(plan_context):
    """Absent halt state constrains nothing — the gate is not a blanket refusal."""
    plan_id = 'halt-absent'
    _make_plan(plan_id)

    result = _check(plan_id, 'operator_question')

    assert result['status'] == 'success'
    assert result['halted'] is False
    assert result['reason'] == 'no_halt_record'


def test_retry_requires_its_attempt(plan_context):
    """A retry without an attempt is refused, naming the workflow's bound."""
    plan_id = 'halt-retry-bound'
    _make_plan(plan_id)
    _record(plan_id)

    result = _check(plan_id, 'retry')

    assert result['status'] == 'error'
    assert result['error'] == 'retry_bound_required'
    assert 'once per finalize invocation' in result['message']


def test_a_retry_bound_wider_than_the_documented_one_is_refused(plan_context):
    """The bound belongs to the workflow: a caller cannot widen the bound it is bound by."""
    plan_id = 'halt-retry-widened'
    _make_plan(plan_id)
    _record(plan_id)

    result = _check(plan_id, 'retry', attempt=2, max_attempts=2)

    assert result['status'] == 'error'
    assert result['error'] == 'retry_bound_not_documented'
    assert result['allowed'] is False


def test_retry_past_its_bound_is_refused(plan_context):
    """A second retry against a bound of one is refused rather than granted."""
    plan_id = 'halt-retry-exhausted'
    _make_plan(plan_id)
    _record(plan_id)

    result = _check(plan_id, 'retry', attempt=2, max_attempts=1)

    assert result['status'] == 'error'
    assert result['error'] == 'retry_bound_exhausted'
    assert result['attempt'] == 2
    assert result['max_attempts'] == 1


def test_retry_with_no_max_attempts_measures_against_the_documented_bound(plan_context):
    """Omitting --max-attempts uses the workflow's bound rather than meaning "no bound"."""
    plan_id = 'halt-retry-default-bound'
    _make_plan(plan_id)
    _record(plan_id)

    admitted = _check(plan_id, 'retry', attempt=1)
    assert admitted['status'] == 'success'
    assert admitted['max_attempts'] == 1

    refused = _check(plan_id, 'retry', attempt=2)
    assert refused['error'] == 'retry_bound_exhausted'


def test_the_check_refuses_a_phase_it_has_no_roster_for(plan_context):
    """The seam is the finalize dispatcher's; another phase is refused, not answered."""
    plan_id = 'halt-other-phase'
    _make_plan(plan_id)

    result = _continuation.check_continuation(
        plan_id=plan_id, phase='5-execute', step=_STEP, continuation='operator_question'
    )

    assert result['status'] == 'error'
    assert result['error'] == 'halt_continuation_refused'
    assert result['allowed'] is False


def test_an_unreadable_plan_is_not_read_as_a_clean_bill_of_health():
    """A plan with no status refuses for the failed READ, never "no halt here"."""
    result = _check('no-such-plan-for-halt-continuation', 'operator_question')

    assert result['status'] == 'error'
    assert result['allowed'] is False
    assert result['error'] in ('plan_not_found', 'status_unavailable')


# ---------------------------------------------------------------------------
# Done when: a resolution after an unanswered escalate_ask is refused
# ---------------------------------------------------------------------------


def test_a_resolution_after_an_escalate_ask_without_an_answer_is_refused(plan_context):
    """``done`` over an unanswered escalation is refused, and nothing is written.

    Done-when clause: *"a step resolution recorded after an `escalate_ask` without
    a logged operator answer is refused"*.
    """
    plan_id = 'halt-escalation-unanswered'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    result = _mark(plan_id, 'done')

    assert result['status'] == 'error', result
    assert result['error'] == 'escalation_unanswered'
    assert result['requested_outcome'] == 'done'
    assert 'halt answer' in result['message']
    # The refusal wrote nothing: no phase-steps record exists for the step.
    status = read_status(plan_id)
    recorded = (status.get('metadata') or {}).get('phase_steps', {}).get(_PHASE, {})
    assert _STEP not in recorded


def test_the_resolution_is_admitted_once_the_operator_answer_is_recorded(plan_context):
    """``halt answer`` unblocks the resolution — the refusal is a gate, not a wall."""
    plan_id = 'halt-escalation-answered'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    answer = cmd_halt_answer(
        Namespace(
            plan_id=plan_id,
            phase=_PHASE,
            step=_STEP,
            selected='Wait another 600s',
        )
    )
    assert answer['status'] == 'success', answer
    assert answer['selected'] == 'Wait another 600s'

    result = _mark(plan_id, 'done')

    assert result['status'] == 'success', result
    assert result['outcome'] == 'done'


def test_a_skipped_resolution_is_refused_on_the_same_terms(plan_context):
    """``skipped`` is a resolution too — it asserts the step needs no further run."""
    plan_id = 'halt-escalation-skipped'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    result = _mark(plan_id, 'skipped')

    assert result['status'] == 'error'
    assert result['error'] == 'escalation_unanswered'


def test_failed_and_loop_back_stay_writable_over_an_open_escalation(plan_context):
    """Progress is not a completion claim: a step may still fail or loop back.

    Without this half the guard would deadlock a step that fails again while the
    operator is deciding, which is the opposite of fail-closed.
    """
    plan_id = 'halt-escalation-progress'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    assert _mark(plan_id, 'failed')['status'] == 'success'
    looped = _mark(plan_id, 'loop_back', loop_back_target='6-finalize')
    assert looped['status'] == 'success', looped


def test_the_continuation_check_narrows_to_operator_question_while_unanswered(plan_context):
    """While the escalation is open, only the operator question is admitted."""
    plan_id = 'halt-escalation-narrowed'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    refused = _check(plan_id, 'retry', attempt=1, max_attempts=1)
    assert refused['status'] == 'error'
    assert refused['error'] == 'escalation_unanswered'
    assert refused['allowed_continuations'] == ['operator_question']
    # The refusal names the step it is about, so a reader is not left guessing.
    assert _STEP in refused['message']

    admitted = _check(plan_id, 'operator_question')
    assert admitted['status'] == 'success'
    assert admitted['escalate_ask'] is True


def test_a_re_recorded_halt_drops_the_previous_answer(plan_context):
    """A fresh halt is a fresh, unanswered stop — a stale answer never carries over."""
    plan_id = 'halt-rehalt'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')
    cmd_halt_answer(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP, selected='Wait another 600s'))

    _record(plan_id, escalate=True, outcome='halted')

    assert _mark(plan_id, 'done')['error'] == 'escalation_unanswered'


# ---------------------------------------------------------------------------
# The store's own refusals
# ---------------------------------------------------------------------------


def test_halt_answer_refuses_a_halt_that_raised_no_escalation(plan_context):
    """An answer to a non-question would record consent nobody gave."""
    plan_id = 'halt-answer-no-escalation'
    _make_plan(plan_id)
    _record(plan_id)

    result = cmd_halt_answer(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP, selected='Yes'))

    assert result['status'] == 'error'
    assert result['error'] == 'no_escalation'


def test_halt_answer_refuses_when_there_is_no_halt_at_all(plan_context):
    """The answer verb names its remedy: record the halt first."""
    plan_id = 'halt-answer-absent'
    _make_plan(plan_id)

    result = cmd_halt_answer(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP, selected='Yes'))

    assert result['status'] == 'error'
    assert result['error'] == 'no_halt_record'


def test_halt_record_requires_a_reason(plan_context):
    """A halt nobody can explain is refused — it would be indistinguishable from a skip."""
    plan_id = 'halt-record-blank'
    _make_plan(plan_id)

    result = cmd_halt_record(
        Namespace(
            plan_id=plan_id,
            phase=_PHASE,
            step=_STEP,
            outcome='failed',
            reason='   ',
            escalate_ask=False,
            option=None,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_an_escalated_halt_must_name_the_options_it_offers(plan_context):
    """Without the offered labels the answer verb could not tell a choice from a paraphrase."""
    plan_id = 'halt-escalate-no-options'
    _make_plan(plan_id)

    result = cmd_halt_record(
        Namespace(
            plan_id=plan_id,
            phase=_PHASE,
            step=_STEP,
            outcome='halted',
            reason='escalate_ask{reason: re_review_timeout}',
            escalate_ask=True,
            option=None,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'
    assert '--option' in result['message']


def test_halt_answer_refuses_a_label_that_was_not_offered(plan_context):
    """The operator's decision is the label they chose, not the caller's summary of it."""
    plan_id = 'halt-answer-not-offered'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    result = cmd_halt_answer(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP, selected='yes, go ahead'))

    assert result['status'] == 'error'
    assert result['error'] == 'selected_not_offered'
    assert result['offered_options'] == ['Wait another 600s', 'Defer merge']
    # ... and the halt is still unanswered, so no resolution may be recorded.
    assert _mark(plan_id, 'done')['error'] == 'escalation_unanswered'


def test_halt_answer_tolerates_case_and_spacing_but_records_the_offered_label(plan_context):
    """A UI may return the label with different case or spacing; the stored answer is canonical."""
    plan_id = 'halt-answer-normalized'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    result = cmd_halt_answer(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP, selected='  wait   ANOTHER 600s '))

    assert result['status'] == 'success', result
    assert result['selected'] == 'Wait another 600s'


def test_a_malformed_halt_record_refuses_both_the_resolution_and_the_continuation(plan_context):
    """An unreadable store is a failed read, never a clean bill of health."""
    plan_id = 'halt-malformed'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['halts'] = {_PHASE: {_STEP: 'not-a-record'}}
    _status_core.write_status(plan_id, status)

    refused_resolution = _mark(plan_id, 'done')
    assert refused_resolution['status'] == 'error'
    assert refused_resolution['error'] == 'halt_unreadable'

    refused_continuation = _check(plan_id, 'operator_question')
    assert refused_continuation['status'] == 'error'
    assert refused_continuation['error'] == 'halt_unreadable'
    assert refused_continuation['allowed'] is False
    # The record demonstrably EXISTS and cannot be read — not "never halted".
    assert refused_continuation['halted'] is True


def test_mark_step_done_failed_records_the_halt_the_roster_calls_one(plan_context):
    """A `failed` outcome IS a halt, so the store must not stay blind on that path.

    Without this, a step failed by a precondition or a timeout wrapper leaves only a
    phase-steps record and `check` answers ``no_halt_record`` for a step that stopped.
    """
    plan_id = 'halt-failed-stamps'
    _make_plan(plan_id)

    result = _mark(plan_id, 'failed')
    assert result['status'] == 'success', result

    continuation = _check(plan_id, 'session_move')
    assert continuation['halted'] is True, 'the failed outcome left no halt for the check to read'
    assert continuation['error'] == 'halt_continuation_refused'


def test_a_failed_outcome_never_overwrites_an_unanswered_escalation(plan_context):
    """The escalation is the operator's to resolve; a later failure must not clear it."""
    plan_id = 'halt-failed-preserves'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    assert _mark(plan_id, 'failed')['status'] == 'success'

    stored = cmd_halt_read(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP))
    assert stored['record']['escalate_ask'] is True
    assert stored['escalation_unanswered'] is True
    assert _mark(plan_id, 'done')['error'] == 'escalation_unanswered'


def test_a_halt_cannot_replace_an_unanswered_escalation(plan_context):
    """Re-recording a halt must not erase the decision the operator has not made yet."""
    plan_id = 'halt-replace-escalation'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    result = cmd_halt_record(
        Namespace(
            plan_id=plan_id,
            phase=_PHASE,
            step=_STEP,
            outcome='failed',
            reason='post-dispatch guard fired again',
            escalate_ask=False,
            option=None,
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'escalation_open'
    # The escalation stands, so the resolution is still refused.
    assert _mark(plan_id, 'done')['error'] == 'escalation_unanswered'


def test_replace_escalation_admits_a_replacement_when_the_operator_instructs_it(plan_context):
    """The protected record is replaceable on the operator's instruction, and only then."""
    plan_id = 'halt-replace-on-instruction'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    replaced = cmd_halt_record(
        Namespace(
            plan_id=plan_id,
            phase=_PHASE,
            step=_STEP,
            outcome='halted',
            reason='the operator asked for a fresh decision on the new evidence',
            escalate_ask=True,
            option=['Ship as is', 'Hold the merge'],
            replace_escalation=True,
        )
    )

    assert replaced['status'] == 'success', replaced
    stored = cmd_halt_read(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP))
    assert stored['record']['options'] == ['Ship as is', 'Hold the merge']
    assert stored['escalation_unanswered'] is True


def test_a_halt_answering_a_question_nobody_asked_is_refused_by_the_record_itself(plan_context):
    """Options belong to an escalation: recording them on a silent halt invents a question."""
    plan_id = 'halt-options-without-escalation'
    _make_plan(plan_id)

    result = cmd_halt_record(
        Namespace(
            plan_id=plan_id,
            phase=_PHASE,
            step=_STEP,
            outcome='failed',
            reason='post-dispatch guard: no terminal record',
            escalate_ask=False,
            option=['Yes'],
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'invalid_argument'


def test_an_escalation_without_offered_options_cannot_be_answered(plan_context):
    """A record that claims an escalation but offers no labels refuses every answer."""
    plan_id = 'halt-words-escalation-no-options'
    _make_plan(plan_id)
    status = read_status(plan_id)
    status.setdefault('metadata', {})['halts'] = {
        _PHASE: {
            _STEP: {
                'outcome': 'halted',
                'reason': 'escalate_ask{reason: re_review_timeout}',
                'escalate_ask': True,
                'recorded_at': '2026-01-01T00:00:00Z',
                'answer': None,
            }
        }
    }
    _status_core.write_status(plan_id, status)

    result = cmd_halt_answer(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP, selected='anything'))

    assert result['status'] == 'error'
    assert result['error'] == 'options_missing'


def test_a_halt_recorded_under_another_key_spelling_is_found_by_the_read_seam(plan_context):
    """Write and read canonicalize the step key identically, so no spelling hides a halt."""
    plan_id = 'halt-key-canonical'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted', step='default:create-pr')

    stored = cmd_halt_read(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP))
    assert stored['recorded'] is True
    assert stored['escalation_unanswered'] is True
    assert _mark(plan_id, 'done')['error'] == 'escalation_unanswered'


def test_halt_read_reports_the_record_and_its_escalation_state(plan_context):
    """The read verb exposes the record and whether its escalation is unanswered."""
    plan_id = 'halt-read'
    _make_plan(plan_id)
    _record(plan_id, escalate=True, outcome='halted')

    one = cmd_halt_read(Namespace(plan_id=plan_id, phase=_PHASE, step=_STEP))
    assert one['recorded'] is True
    assert one['escalation_unanswered'] is True
    assert one['record']['outcome'] == 'halted'

    every = cmd_halt_read(Namespace(plan_id=plan_id, phase=None, step=None))
    assert every['count'] == 1
    assert every['records'][0]['step'] == _STEP


# ---------------------------------------------------------------------------
# The roster is declared once and mirrored, not restated twice
# ---------------------------------------------------------------------------


def _declared_roster() -> list[str]:
    """The roster tokens declared by the dispatcher document's own table."""
    text = _DISPATCHER_DOC.read_text(encoding='utf-8')
    heading = '#### Halt continuation roster'
    assert heading in text, (
        f'{_DISPATCHER_DOC.name} no longer carries the {heading!r} section, so the roster this '
        'script mirrors is undeclared'
    )
    section = text.split(heading, 1)[1]
    # The next heading of any level ends the section.
    section = re.split(r'\n#{2,4} ', section, maxsplit=1)[0]
    return _ROSTER_ROW_RE.findall(section)


def test_the_declared_roster_matches_the_script():
    """The document's roster and the script's admitted set are the same set.

    Cross-derived rather than compared against a literal here, so editing either
    side alone fails the build instead of silently diverging.
    """
    declared = _declared_roster()
    admitted = sorted(_continuation.NAMED_CONTINUATIONS)

    assert declared, (
        "the roster table parsed empty — the document's table shape changed and this guard "
        'would otherwise pass over nothing'
    )
    assert sorted(declared) == admitted, (
        f'{_DISPATCHER_DOC.name} declares {sorted(declared)} but halt_continuation admits '
        f'{admitted}. The roster is declared once, in the document, and mirrored by the script.'
    )


# ---------------------------------------------------------------------------
# The handshake override requires the operator's answer (D1)
# ---------------------------------------------------------------------------


def _capture_args(**overrides):
    base = {
        'plan_id': 'handshake-override',
        'phase': '5-execute',
        'override': True,
        'reason': 'the caller believes the drift is legitimate',
        'operator_answer': None,
        'override_basis': 'operator',
        'loop_back_marker': False,
        'strict': False,
    }
    base.update(overrides)
    return Namespace(**base)


def test_handshake_override_refuses_to_run_on_a_caller_rationale_alone():
    """``--override`` without an operator answer is refused before any capture work.

    D1: a refused phase transition is never overridden by the main context — the
    reason is the caller's own words, and only the operator can supply the answer.
    """
    result = cmd_capture(_capture_args())

    assert result['status'] == 'error'
    assert result['error'] == 'missing_operator_answer'


def test_handshake_override_accepts_a_recorded_operator_answer_past_that_gate():
    """With an answer supplied, the refusal no longer fires.

    The capture itself legitimately fails in this fixture (no plan, no
    invariants), which is exactly the point: the assertion is that the
    operator-answer gate is passed, not that the capture succeeded.
    """
    result = cmd_capture(_capture_args(operator_answer='Yes — the drift is legitimate, proceed'))

    assert result.get('error') != 'missing_operator_answer'


def test_scheduled_loop_back_override_refuses_a_fabricated_operator_answer():
    """The one sanctioned non-operator basis records NO answer rather than inventing one."""
    result = cmd_capture(
        _capture_args(
            override_basis='scheduled_loop_back',
            loop_back_marker=True,
            operator_answer='pretend the operator said yes',
        )
    )

    assert result['status'] == 'error'
    assert result['error'] == 'operator_answer_on_scheduled_override'


def test_the_scheduled_basis_is_admitted_only_with_the_in_process_marker():
    """With the marker observed in-process, the basis passes its own gate.

    The capture itself then fails in this fixture (no plan, no invariants); the
    assertion is that neither override-authority refusal fired, not that the
    capture succeeded.
    """
    result = cmd_capture(_capture_args(override_basis='scheduled_loop_back', loop_back_marker=True))

    assert result.get('error') not in ('scheduled_override_without_marker', 'missing_operator_answer')


def test_scheduled_loop_back_basis_is_refused_when_no_marker_schedules_the_drift():
    """The reserved basis is a fact about the plan, not a flag the caller may choose.

    Without this half, ``--override-basis scheduled_loop_back`` would be a second
    spelling of "override without asking" — exactly what the operator-answer gate
    exists to remove.
    """
    result = cmd_capture(_capture_args(override_basis='scheduled_loop_back'))

    assert result['status'] == 'error'
    assert result['error'] == 'scheduled_override_without_marker'


def test_an_unknown_override_basis_is_refused():
    """Only the two named bases exist; anything else would persist an unnameable authority."""
    result = cmd_capture(_capture_args(override_basis='other'))

    assert result['status'] == 'error'
    assert result['error'] == 'unknown_override_basis'


def test_operator_answer_without_an_override_is_refused():
    """An ordinary capture records no override, so an answer on it would describe a grant that never happened."""
    result = cmd_capture(_capture_args(override=False, reason=None, operator_answer='yes, go ahead'))

    assert result['status'] == 'error'
    assert result['error'] == 'operator_answer_without_override'


def test_the_handshake_row_field_list_declares_both_columns():
    """The persisted row shape keeps the answer and what authorized it apart."""
    fields = _handshake_store.HANDSHAKE_FIELDS

    assert 'operator_answer' in fields
    assert 'override_basis' in fields


def test_the_capture_row_records_the_basis_and_withholds_a_scheduled_answer():
    """The scheduled auto-override's row carries NO answer — the claim is pinned at the row."""
    scheduled = _handshake._row_for_capture(
        'row-shape',
        '5-execute',
        {},
        {},
        override=True,
        override_reason='loop-back re-entry auto-override (scheduled by 5-execute loop_back)',
        operator_answer='',
        override_basis='scheduled_loop_back',
    )

    assert scheduled['override_basis'] == 'scheduled_loop_back'
    assert scheduled['operator_answer'] == ''

    answered = _handshake._row_for_capture(
        'row-shape',
        '5-execute',
        {},
        {},
        override=True,
        override_reason='operator accepted the drift',
        operator_answer='yes, the drift is legitimate',
        override_basis='operator',
    )

    assert answered['override_basis'] == 'operator'
    assert answered['operator_answer'] == 'yes, the drift is legitimate'
