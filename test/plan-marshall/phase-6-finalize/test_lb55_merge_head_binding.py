#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""PLAN-LB-55 D1 — the merge barrier refuses a candidate its gates never saw.

``pre_merge_gate merge`` dispatched the merge verb on a clean findings store alone.
Every head-dependent finalize gate stamps ``head_at_completion``, and nothing
compared those stamps with the tree being merged, so a run could ship a head its
gates had never seen (PLAN-LB-26: gates stamped ``3db65fc05``, ``74e6bfda`` merged).
"""

from __future__ import annotations

import pytest

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', register=False)

HEAD_GATED = 'a' * 40
HEAD_MERGED = 'b' * 40


def _status(head_by_step: dict[str, str | None]) -> dict:
    """A status payload whose 6-finalize step records carry ``head_at_completion``."""
    steps = {
        step: ({'outcome': 'done', 'head_at_completion': head} if head else {'outcome': 'done'})
        for step, head in head_by_step.items()
    }
    return {'metadata': {'phase_steps': {'6-finalize': steps}}}


def _merge(status, head, **kwargs):
    """Run the gate with stubbed findings, participation and merge seams.

    Participation is stubbed COMPLETE here because this module's subject is the head
    binding: the production participation reader spawns its own provider and predicate
    subprocesses, and LB-100's participation behaviour has its own cases in
    ``test_pre_merge_gate.py``.

    Head-dependence discovery and the verdict-currency classifier are stubbed too, for
    the same reason: the production forms read the repository's own finalize-step docs
    and spawn a ``verdict_currency`` executor call. A case that exercises one of those
    paths overrides the corresponding seam, and the production classifier has its own
    case in this module.
    """
    kwargs.setdefault(
        'participation_check',
        lambda _pid, _pr, _project_dir: {
            'status': 'success',
            'participation_complete': True,
            'roster_read': True,
            'required_bots': ['coderabbit'],
            'unproven_bots': [],
            'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
        },
    )
    kwargs.setdefault('head_dependence_reader', lambda _step: (True, None))
    kwargs.setdefault(
        'classifier',
        lambda _step, _project_dir, _recorded: {'status': 'success', 'verdict': 'invalidated', 'reason': 'stub'},
    )
    return gate.merge(
        'lb55-plan',
        route='safe-merge',
        pr_number=7,
        project_dir='/tmp/does-not-matter',
        strategy='squash',
        findings_check=lambda _pid: {'status': 'success', 'blocking_count': 0},
        merge_runner=lambda _args: {'status': 'success', 'merged': True},
        status_reader=lambda _pid: status,
        head_reader=lambda _dir: head,
        **kwargs,
    )


def test_a_merge_candidate_newer_than_the_functional_review_head_refuses():
    """The PLAN-LB-26 shape: the gates stamped one head, the merge ships another."""
    status = _status(
        {
            'functional-review': HEAD_GATED,
            'pre-push-quality-gate': HEAD_GATED,
        }
    )

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert result['dispatched'] is False, 'nothing may be dispatched on a refused head'
    named = {item['step'] for item in result['steps']}
    assert named == {'functional-review', 'pre-push-quality-gate'}
    for item in result['steps']:
        assert item['recorded_head'] == HEAD_GATED
        assert item['head'] == HEAD_MERGED


def test_the_same_records_at_the_candidate_head_dispatch_the_merge():
    """⛔ MATCHED CONTROL — same records, candidate equal to them, the merge dispatches."""
    status = _status({'functional-review': HEAD_MERGED, 'pre-push-quality-gate': HEAD_MERGED})

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'success'
    assert result['dispatched'] is True
    assert result['findings_gate'] == 'clean'


def test_a_record_carrying_no_head_is_not_consulted():
    """A step that stamped no SHA was never anchored to a tree; the re-entry check owns it."""
    status = _status({'functional-review': None, 'code-review': None})

    result = _merge(status, HEAD_MERGED)

    assert result['dispatched'] is True, f'an unstamped record must not be read as a mismatch: {result!r}'


@pytest.mark.parametrize('status', [None, {}, {'metadata': {}}], ids=['unreadable', 'empty', 'no-steps'])
def test_an_unreadable_or_empty_status_passes(status):
    """Nothing recorded means nothing to compare — never a fabricated mismatch."""
    result = _merge(status, HEAD_MERGED)

    assert result['dispatched'] is True


def test_an_unreadable_local_head_passes():
    """A candidate that cannot be read is not a candidate that differs."""
    status = _status({'functional-review': HEAD_GATED})

    result = _merge(status, None)

    assert result['dispatched'] is True


# ---------------------------------------------------------------------------
# PLAN-LB-107 D1 — the merge gate honours the operator's re-fire waiver
# ---------------------------------------------------------------------------
#
# The dispatcher's re-entry table SKIPs a head-dependent step whose
# ``refire_waiver.head`` equals the live HEAD. The gate used to ignore the
# waiver entirely, so a step the operator had explicitly waived was refused
# again at merge — and the waived reviews ran again hours later. Every case
# below is paired: a waiver honoured at its own head, and the same waiver void
# at any other head, so neither direction can pass by refusing (or admitting)
# everything.

HEAD_C = 'c' * 40


def _status_with_waivers(head_by_step: dict[str, str | None], waivers: dict[str, object]) -> dict:
    """A status payload whose records carry the given ``refire_waiver`` values."""
    status = _status(head_by_step)
    steps = status['metadata']['phase_steps']['6-finalize']
    for step, waiver in waivers.items():
        steps[step]['refire_waiver'] = waiver
    return status


def test_a_waiver_at_the_candidate_head_is_honoured_and_named_in_the_payload():
    """(a) Record at A, waiver at B == candidate: the merge dispatches."""
    status = _status_with_waivers(
        {'functional-review': HEAD_GATED},
        {'functional-review': {'head': HEAD_MERGED, 'basis': 'operator accepted the stale review'}},
    )

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'success', result
    assert result['dispatched'] is True
    assert result['waived_steps'] == [
        {
            'step': 'functional-review',
            'waiver_head': HEAD_MERGED,
            'basis': 'operator accepted the stale review',
        }
    ]


def test_a_waiver_at_any_other_head_is_void_and_the_step_is_refused():
    """(b) MATCHED CONTROL: the same waiver at C != candidate is void."""
    status = _status_with_waivers(
        {'functional-review': HEAD_GATED},
        {'functional-review': {'head': HEAD_C, 'basis': 'waived for another tree'}},
    )

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert {item['step'] for item in result['steps']} == {'functional-review'}
    assert 'waived_steps' not in result


@pytest.mark.parametrize(
    'waiver',
    [
        {'basis': 'no head at all'},
        {'head': 'abc1234', 'basis': 'abbreviated'},
        'not-a-dict',
        {'head': None},
    ],
    ids=['no-head', 'abbreviated', 'not-a-dict', 'head-is-null'],
)
def test_a_malformed_waiver_is_void_and_the_step_is_refused(waiver):
    """(c) A malformed waiver is never a get-out-of-jail key."""
    status = _status_with_waivers({'functional-review': HEAD_GATED}, {'functional-review': waiver})

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert {item['step'] for item in result['steps']} == {'functional-review'}


def test_a_waiver_on_one_step_does_not_admit_a_second_stale_step():
    """(d) A waiver is per step, never a blanket admission for the record set."""
    status = _status_with_waivers(
        {'functional-review': HEAD_GATED, 'pre-push-quality-gate': HEAD_GATED},
        {'functional-review': {'head': HEAD_MERGED, 'basis': 'waived'}},
    )

    result = _merge(status, HEAD_MERGED)

    assert result['status'] == 'error'
    assert {item['step'] for item in result['steps']} == {'pre-push-quality-gate'}


# ---------------------------------------------------------------------------
# PLAN-LB-107 D2 — head-dependence comes from the declared fact
# ---------------------------------------------------------------------------
#
# The dispatcher decides head-dependence from the step doc's own
# ``head_dependent: true``; the gate decided it from whether a SHA happened to
# be on the record. An undeclared step that carried a stamp could therefore be
# refused with a remedy ("re-run those steps") the dispatcher would never act
# on, because it never re-fires that step at all.


def test_an_undeclared_step_with_a_stale_stamp_is_listed_not_refused():
    """(a) An undeclared stamp is evidence, never an offence."""
    status = _status({'finalize-step-sync-baseline': HEAD_GATED})

    result = _merge(status, HEAD_MERGED, head_dependence_reader=lambda _step: (False, None))

    assert result['status'] == 'success', result
    assert result['dispatched'] is True
    assert result['unconsulted_stamps'] == [
        {'step': 'finalize-step-sync-baseline', 'recorded_head': HEAD_GATED},
    ]


def test_a_declared_step_with_the_same_stale_stamp_refuses():
    """(b) MATCHED CONTROL: the declared fact makes the same stamp an offence."""
    status = _status({'finalize-step-sync-baseline': HEAD_GATED})

    result = _merge(status, HEAD_MERGED, head_dependence_reader=lambda _step: (True, None))

    assert result['status'] == 'error'
    assert {item['step'] for item in result['steps']} == {'finalize-step-sync-baseline'}


def test_an_underivable_declaration_falls_back_to_field_presence_and_says_so():
    """(c) Discovery failure is fail-closed, and the payload names the fallback."""
    status = _status({'functional-review': HEAD_GATED})

    result = _merge(
        status,
        HEAD_MERGED,
        head_dependence_reader=lambda _step: (False, 'find_implementors raised'),
    )

    assert result['status'] == 'error'
    assert result['error'] == gate.MERGE_HEAD_NOT_GATED
    assert result['head_dependence_fallback'] == [
        {'step': 'functional-review', 'reason': 'find_implementors raised'},
    ]


@pytest.mark.parametrize(
    ('verdict', 'dispatched'),
    [('preserved', True), ('invalidated', False)],
)
def test_the_classifier_decides_a_stale_declared_step(verdict, dispatched):
    """(d) The classifier's own verdict is what admits or refuses the record."""
    status = _status({'functional-review': HEAD_GATED})

    result = _merge(
        status,
        HEAD_MERGED,
        classifier=lambda _step, _project_dir, _recorded: {'status': 'success', 'verdict': verdict},
    )

    assert result['dispatched'] is dispatched
    if dispatched:
        assert result['status'] == 'success'
    else:
        assert result['error'] == gate.MERGE_HEAD_NOT_GATED


def test_the_production_classifier_is_reached_through_the_executor_seam(monkeypatch):
    """(d) The default classifier asks ``verdict_currency classify`` like every other verb."""
    calls: list[tuple[str, list[str]]] = []

    def _fake_run_verb(notation, argv, **_kwargs):
        calls.append((notation, list(argv)))
        return {'status': 'success', 'verdict': 'preserved', 'step': 'functional-review'}

    monkeypatch.setattr(gate, '_run_verb', _fake_run_verb)
    status = _status({'functional-review': HEAD_GATED})

    result = gate.merge(
        'lb55-plan',
        route='safe-merge',
        pr_number=7,
        project_dir='/abs/worktree',
        strategy='squash',
        findings_check=lambda _pid: {'status': 'success', 'blocking_count': 0},
        merge_runner=lambda _args: {'status': 'success', 'merged': True},
        status_reader=lambda _pid: status,
        head_reader=lambda _dir: HEAD_MERGED,
        participation_check=lambda _pid, _pr, _project_dir: {
            'status': 'success',
            'participation_complete': True,
            'roster_read': True,
            'required_bots': ['coderabbit'],
            'unproven_bots': [],
            'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
        },
        head_dependence_reader=lambda _step: (True, None),
    )

    assert result['dispatched'] is True
    assert calls == [
        (
            'plan-marshall:phase-6-finalize:verdict_currency',
            [
                'classify',
                '--step',
                'functional-review',
                '--worktree-path',
                '/abs/worktree',
                '--head-at-completion',
                HEAD_GATED,
                '--live-head',
                HEAD_MERGED,
            ],
        )
    ]


@pytest.mark.parametrize(
    ('step', 'expected'),
    [('functional-review', True), ('finalize-step-sync-baseline', False)],
)
def test_the_production_discovery_path_resolves_the_declared_fact(step, expected):
    """Anti-vacuity: the gate's default reader really reaches the step docs.

    Every other D2 case stubs this seam. If the import path, the discovery call or
    the frontmatter read stopped working, the gate would fall back to field presence
    forever and those cases would stay green — so this one asserts the real reader
    against the repository's own declared and undeclared steps.
    """
    assert gate._head_dependence(step) == (expected, None)
