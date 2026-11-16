#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The merge barrier refuses while a manifest step ordered before it has no record.

``branch-cleanup`` (order 70) is the merge gate, but nothing until now asked
whether the steps the manifest orders BELOW it actually ran. A step skipped late
in a hand-driven final round, for example ``adr-propose`` (order 62), surfaced
only at the tail — after the merge and the worktree removal — through the
end-of-phase ``phase_steps_complete`` handshake.

``pre_merge_gate merge`` therefore sweeps ``phase_6.steps`` up to the
``branch-cleanup`` entry and asks the existing step-record assertion about each
of those steps. The load-bearing property under test is NEGATIVE: with any one
of them lacking a terminal record, the injected merge runner is NEVER invoked —
with the positive controls that a fully recorded sequence reaches it exactly
once, that a step the manifest never selected is not consulted at all, and that
a re-entry after the record lands admits the merge.
"""

from __future__ import annotations

import pytest

from conftest import load_script_module

gate = load_script_module('plan-marshall', 'phase-6-finalize', 'pre_merge_gate.py', register=False)

_PLAN_ID = 'lb157-plan'
_HEAD = 'c' * 40
_BRANCH_CLEANUP = 'default:branch-cleanup'

#: A phase-6 record that survives ``assert-step-recorded --require-terminal``.
_RECORDED = {'status': 'success', 'recorded': True, 'firing_count': 1}

_PARTICIPATION_COMPLETE = {
    'status': 'success',
    'participation_complete': True,
    'roster_read': True,
    'required_bots': ['coderabbit'],
    'optional_bots': [],
    'unproven_bots': [],
    'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
}

_NO_AUTHORIZATION = {
    'status': 'success',
    'any_authorized': False,
    'any_admissible': False,
    'authorized_kinds': [],
    'inadmissible_kinds': [],
    'lapsed_kinds': [],
}


@pytest.fixture(autouse=True)
def _merge_mutex_held(monkeypatch: pytest.MonkeyPatch) -> None:
    """Autouse: stand in for the merge-mutex reader, answering "held by this plan".

    Every case here is about the step sequence, so each one needs the mutex proof
    satisfied and none of them should depend on whether the machine running the
    suite happens to hold the real repository's ``.plan/local/merge.lock``. The
    proof itself has its own module (``test_pre_merge_gate_merge_lock_proof.py``).
    """
    monkeypatch.setattr(
        gate,
        '_merge_lock_holder_read',
        lambda: {'state': 'held', 'holder': _PLAN_ID, 'lock_path': '<test>'},
    )


class _Runner:
    """Recording merge-runner seam: returns a canned verb payload and logs every call."""

    def __init__(self) -> None:
        self.calls: list[list[str]] = []

    def __call__(self, ci_args: list[str]) -> dict:
        self.calls.append(list(ci_args))
        return {'status': 'success', 'merged': True}


class _Spy:
    """Recording step-record seam: answers from a step -> verdict map, logging queries."""

    def __init__(self, records: dict[str, dict]) -> None:
        self.records = records
        self.asked: list[str] = []

    def __call__(self, step: str) -> dict:
        self.asked.append(step)
        verdict = self.records.get(step)
        if verdict is None:
            return _missing_record(step)
        return dict(verdict)


def _missing_record(step: str) -> dict:
    """The assertion's own refusal payload for a step with no terminal record."""
    return {
        'status': 'error',
        'error': 'step_record_missing',
        'phase': '6-finalize',
        'step': step,
        'recorded': False,
        'outcome': None,
        'message': f'No terminal record for step {step!r} in phase 6-finalize.',
    }


def _record(outcome: str) -> dict:
    """A terminal record with ``outcome`` (done / skipped / loop_back / failed)."""
    return {**_RECORDED, 'outcome': outcome}


def _manifest(*steps: str, status: str = 'success') -> dict:
    """A manifest read payload whose ``phase_6.steps`` is ``steps``, in order."""
    if status != 'success':
        return {'status': status, 'error': 'file_not_found', 'message': 'no manifest'}
    return {'status': 'success', 'plan_id': _PLAN_ID, 'phase_6': {'steps': list(steps)}}


def _merge(*, manifest: dict, records: dict[str, dict], route: str = 'safe-merge'):
    """Drive ``merge`` with the step-sequence sweep delegated to the production code.

    The sweep itself is stubbed through ``step_sequence_check`` — the merge-path
    seam — while the delegation runs the REAL :func:`pre_merge_gate._step_sequence_refusal`
    over stubbed manifest and step-record readers. That is what makes these cases
    exercise the production sweep rather than an assembled verdict, without a
    manifest file or a status document on disk.
    """
    runner = _Runner()
    spy = _Spy(records)
    result = gate.merge(
        _PLAN_ID,
        route=route,
        pr_number=42,
        project_dir='/abs/worktree',
        strategy='squash' if route == 'safe-merge' else None,
        findings_check=lambda _plan_id: {'status': 'success', 'blocking_count': 0},
        merge_runner=runner,
        head_reader=lambda _project_dir: _HEAD,
        status_reader=lambda _plan_id: None,
        participation_check=lambda _plan_id, _pr, _project_dir: dict(_PARTICIPATION_COMPLETE),
        authorization_check=lambda _plan_id, _head: dict(_NO_AUTHORIZATION),
        step_sequence_check=lambda plan_id: gate._step_sequence_refusal(
            plan_id,
            manifest_reader=lambda _plan_id: manifest,
            step_record_check=spy,
        ),
    )
    return result, runner, spy


# --------------------------------------------------------------------------- #
# The four cases the spec enumerates
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize('route', gate.ROUTES)
def test_one_unrecorded_earlier_step_refuses_the_merge(route: str) -> None:
    """A skipped earlier step refuses the merge and names the step it names."""
    result, runner, _spy = _merge(
        manifest=_manifest(
            'default:pre-push-quality-gate',
            'default:create-pr',
            _BRANCH_CLEANUP,
            'default:record-metrics',
        ),
        records={
            # default:create-pr never landed a terminal record — the skip this plan catches.
            'default:pre-push-quality-gate': _record('done'),
        },
        route=route,
    )

    assert runner.calls == [], f'the merge runner was invoked over an unrecorded step: {runner.calls}'
    assert result['status'] == 'error'
    assert result['dispatched'] is False
    assert result['error'] == gate.MERGE_EARLIER_STEP_UNRECORDED
    assert [row['step'] for row in result['steps']] == ['default:create-pr'], result['steps']
    assert result['steps'][0]['reason'] == 'step_record_missing'
    assert 'default:create-pr' in result['message']
    assert 'findings_gate' not in result


def test_every_earlier_step_recorded_admits_the_merge() -> None:
    """With every earlier step terminal, the routed merge verb is issued once."""
    result, runner, spy = _merge(
        manifest=_manifest('default:create-pr', 'default:adr-propose', _BRANCH_CLEANUP),
        records={
            'default:create-pr': _record('done'),
            'default:adr-propose': _record('skipped'),
        },
    )

    assert result['dispatched'] is True, result
    assert result['findings_gate'] == 'clean'
    assert len(runner.calls) == 1
    # Non-vacuity: both earlier steps really were consulted.
    assert spy.asked == ['default:create-pr', 'default:adr-propose']


def test_adr_propose_absent_from_the_manifest_admits_the_merge() -> None:
    """A step the manifest never selected (``adr-propose``, ``default_on: false``) cannot block.

    Applicability is the manifest's own answer: a step excluded by its
    ``default_on`` / lane resolution is absent from ``phase_6.steps``, so the sweep
    has no record to demand and must not invent one.
    """
    result, runner, spy = _merge(
        manifest=_manifest('default:create-pr', _BRANCH_CLEANUP),
        records={'default:create-pr': _record('done')},
    )

    assert result['dispatched'] is True, result
    assert len(runner.calls) == 1
    assert spy.asked == ['default:create-pr'], spy.asked
    assert 'default:adr-propose' not in spy.asked


def test_re_entry_after_the_step_is_recorded_admits_the_merge() -> None:
    """The refusal is a re-entry, not a dead end: once the step runs, the merge proceeds."""
    manifest = _manifest('default:create-pr', 'default:adr-propose', _BRANCH_CLEANUP)
    records: dict[str, dict] = {'default:create-pr': _record('done')}

    first, first_runner, _spy = _merge(manifest=manifest, records=records)

    assert first['dispatched'] is False
    assert [row['step'] for row in first['steps']] == ['default:adr-propose']
    assert first_runner.calls == []

    # The dispatcher re-entered finalize and adr-propose landed its terminal record.
    records['default:adr-propose'] = _record('done')

    second, second_runner, _spy2 = _merge(manifest=manifest, records=records)

    assert second['dispatched'] is True, second
    assert len(second_runner.calls) == 1


# --------------------------------------------------------------------------- #
# The boundary of the sweep: which steps it asks about, and which outcomes admit
# --------------------------------------------------------------------------- #


def test_steps_ordered_after_branch_cleanup_are_not_checked() -> None:
    """The sweep stops at ``branch-cleanup``: post-merge steps have not run yet."""
    result, runner, spy = _merge(
        manifest=_manifest(
            'default:create-pr',
            _BRANCH_CLEANUP,
            'default:record-metrics',
            'default:archive-plan',
        ),
        records={'default:create-pr': _record('done')},
    )

    assert result['dispatched'] is True, result
    assert len(runner.calls) == 1
    assert spy.asked == ['default:create-pr'], spy.asked


@pytest.mark.parametrize('outcome', ['done', 'skipped', 'loop_back'])
def test_a_terminal_non_failure_outcome_does_not_block(outcome: str) -> None:
    """``done`` / ``skipped`` / ``loop_back`` are the outcomes the spec admits.

    Every ``6-finalize`` record carries a ``display_detail`` by construction
    (mark-step-done refuses one without it) and every ``loop_back`` carries a
    ``loop_back_target``, so "with a reason" is satisfied by the record's own shape
    rather than by a second field read here.
    """
    result, runner, _spy = _merge(
        manifest=_manifest('default:adr-propose', _BRANCH_CLEANUP),
        records={'default:adr-propose': _record(outcome)},
    )

    assert result['dispatched'] is True, result
    assert len(runner.calls) == 1


def test_a_failed_earlier_step_refuses_the_merge() -> None:
    """``failed`` is terminal but not a completion, so the merge is refused."""
    result, runner, _spy = _merge(
        manifest=_manifest('default:pre-push-quality-gate', _BRANCH_CLEANUP),
        records={'default:pre-push-quality-gate': _record('failed')},
    )

    assert runner.calls == []
    assert result['dispatched'] is False
    assert result['error'] == gate.MERGE_EARLIER_STEP_UNRECORDED
    assert result['steps'] == [
        {'step': 'default:pre-push-quality-gate', 'reason': 'step_record_failed', 'outcome': 'failed'}
    ]


def test_a_mis_keyed_orphan_record_refuses_the_merge() -> None:
    """A record under the wrong key is not a record for this step."""
    result, runner, _spy = _merge(
        manifest=_manifest('default:adr-propose', _BRANCH_CLEANUP),
        records={
            'default:adr-propose': {
                'status': 'error',
                'error': 'step_record_mismatched_key',
                'phase': '6-finalize',
                'step': 'default:adr-propose',
                'recorded': False,
                'outcome': None,
                'orphan_key': 'adr-propose',
                'orphan_outcome': 'done',
            }
        },
    )

    assert runner.calls == []
    assert result['dispatched'] is False
    assert result['steps'][0]['reason'] == 'step_record_mismatched_key'


def test_an_unreadable_manifest_refuses_the_merge() -> None:
    """An unreadable manifest is a refusal, never a vacuous empty sequence."""
    result, runner, spy = _merge(manifest=_manifest(_BRANCH_CLEANUP, status='error'), records={})

    assert runner.calls == []
    assert result['dispatched'] is False
    assert result['error'] == gate.MERGE_EARLIER_STEP_UNRECORDED
    assert result['reason'] == 'manifest_unreadable'
    assert spy.asked == [], 'the sweep demanded records from an unreadable manifest'


def test_a_manifest_without_branch_cleanup_refuses_the_merge() -> None:
    """No ``branch-cleanup`` entry means there is no sequence to stand on: fail closed."""
    result, runner, _spy = _merge(
        manifest=_manifest('default:create-pr', 'default:record-metrics'),
        records={'default:create-pr': _record('done')},
    )

    assert runner.calls == []
    assert result['dispatched'] is False
    assert result['reason'] == 'branch_cleanup_absent_from_manifest'


def test_the_refusal_is_a_distinct_merge_gate_code() -> None:
    """The new refusal joins the gate's vocabulary without reusing a sibling's code."""
    assert gate.MERGE_EARLIER_STEP_UNRECORDED == 'merge_earlier_step_unrecorded'
    assert gate.MERGE_EARLIER_STEP_UNRECORDED not in {
        gate.MERGE_LOCK_NOT_HELD,
        gate.MERGE_HEAD_NOT_GATED,
        gate.MERGE_PARTICIPATION_UNPROVEN,
        'blocking_findings_present',
        'query_failed',
    }
    assert 'MERGE_EARLIER_STEP_UNRECORDED' in gate.__all__


@pytest.mark.parametrize('route', gate.ROUTES)
def test_the_refusal_carries_no_invocation_category(route: str) -> None:
    """It is a gate verdict, not a malformed call: the category field stays absent."""
    result, _runner, _spy = _merge(
        manifest=_manifest('default:create-pr', _BRANCH_CLEANUP),
        records={},
        route=route,
    )

    assert result['dispatched'] is False
    assert gate.REFUSAL_CATEGORY_FIELD not in result, result
