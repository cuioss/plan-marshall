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
    """
    kwargs.setdefault(
        'participation_check',
        lambda _pid, _pr: {
            'status': 'success',
            'participation_complete': True,
            'roster_read': True,
            'required_bots': ['coderabbit'],
            'unproven_bots': [],
            'bot_states': [{'bot_kind': 'coderabbit', 'state': 'participated'}],
        },
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
