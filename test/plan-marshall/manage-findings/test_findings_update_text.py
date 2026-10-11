#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``_findings_core.update_finding_text``: the in-place text update of a re-read source.

The verb updates ONE record and never files a second. Whether it reopens a resolved
finding is decided by whether the quarantined text moved; ``reviewed_commit_sha``
moves only where no disposition survives the update; and text that quarantines to
nothing is refused with the record left as it was.
"""

import pytest

from conftest import load_script_module

_findings_core = load_script_module('plan-marshall', 'manage-findings', '_findings_core.py', '_findings_core')

PLAN_ID = 'update-text'
PLAN_IDS = (PLAN_ID,)

_HEAD_A = 'a' * 40
_HEAD_B = 'b' * 40
_FIX_COMMIT = 'c' * 40
_OLD_BODY = 'The summary reports nothing further on this pass.'
_NEW_BODY = 'The retry helper drops the final attempt when max_attempts is 1.'
_OLD_DETAIL = 'comment_id: 7\nedit_term: 2026-01-01T00:00:01Z'
_NEW_DETAIL = 'comment_id: 7\nedit_term: 2026-01-01T00:00:09Z'


def _stored(*, fixed: bool = False) -> str:
    """File a pr-comment finding at ``_HEAD_A``; optionally resolve it ``fixed``, stamped and responded."""
    added = _findings_core.add_finding(
        PLAN_ID,
        'pr-comment',
        'PR #1 issue_comment comment by bot (7)',
        _OLD_DETAIL,
        reviewed_commit_sha=_HEAD_A,
        raw_input={'body': _OLD_BODY},
    )
    hash_id: str = added['hash_id']
    if fixed:
        resolved = _findings_core.resolve_finding(PLAN_ID, hash_id, 'fixed', detail='Fixed.', fix_task_number=3)
        assert resolved['status'] == 'success', resolved
        assert _findings_core.stamp_fix_commit(PLAN_ID, _FIX_COMMIT, fix_task_number=3)['hash_ids'] == [hash_id]
        assert _findings_core.mark_finding_responded(PLAN_ID, hash_id)['status'] == 'success'
    return hash_id


def _update(hash_id: str, body: str | None, **kwargs) -> dict:
    raw_input = {} if body is None else {'body': body}
    result: dict = _findings_core.update_finding_text(
        PLAN_ID, hash_id, detail=_NEW_DETAIL, raw_input=raw_input, reviewed_commit_sha=_HEAD_B, **kwargs
    )
    return result


def _record(hash_id: str) -> dict:
    record: dict = _findings_core.get_finding(PLAN_ID, hash_id)
    return record


def test_a_pending_finding_takes_the_new_text_and_the_new_anchor(plan_context):
    hash_id = _stored()

    result = _update(hash_id, _NEW_BODY)

    assert (result['status'], result['outcome'], result['resolution']) == ('success', 'updated', 'pending')
    record = _record(hash_id)
    assert (record['detail'], record['raw_input']['body']) == (_NEW_DETAIL, _NEW_BODY)
    assert record['reviewed_commit_sha'] == _HEAD_B


def test_a_changed_body_reopens_a_resolved_finding_and_clears_its_disposition(plan_context):
    """The disposition, fix stamp, fix task and ``responded`` marker all belonged to the replaced text."""
    hash_id = _stored(fixed=True)

    result = _update(hash_id, _NEW_BODY)

    assert (result['outcome'], result['resolution']) == ('reopened', 'pending')
    record = _record(hash_id)
    assert (record['resolution'], record['resolution_detail']) == ('pending', None)
    assert record[_findings_core.FIX_COMMIT_FIELD] is None
    assert record[_findings_core.FIX_TASK_FIELD] is None
    assert record['responded'] is False
    assert (record['detail'], record['raw_input']['body']) == (_NEW_DETAIL, _NEW_BODY)
    assert record['reviewed_commit_sha'] == _HEAD_B


def test_an_identical_body_keeps_the_resolution_and_its_anchor(plan_context):
    """⛔ MATCHED CONTROL — only the edit term moves; the anchor of the kept ``fixed`` disposition stays."""
    hash_id = _stored(fixed=True)

    result = _update(hash_id, _OLD_BODY)

    assert (result['outcome'], result['resolution']) == ('kept_resolved', 'fixed')
    record = _record(hash_id)
    assert (record['resolution'], record['resolution_detail']) == ('fixed', 'Fixed.')
    assert record[_findings_core.FIX_COMMIT_FIELD] == _FIX_COMMIT
    assert record['responded'] is True
    assert (record['detail'], record['raw_input']['body']) == (_NEW_DETAIL, _OLD_BODY)
    assert record['reviewed_commit_sha'] == _HEAD_A


@pytest.mark.parametrize(
    ('body', 'cap_kwargs'),
    [('', {}), (None, {}), (_NEW_BODY, {'raw_input_max_bytes': 0})],
    ids=['empty-body', 'no-raw-input', 'wholly-over-cap'],
)
def test_text_that_quarantines_to_nothing_is_refused_and_leaves_the_record_unchanged(plan_context, body, cap_kwargs):
    """The new edit term is never recorded over the old body, and the old body is never erased."""
    hash_id = _stored(fixed=True)
    before = _record(hash_id)

    result = _update(hash_id, body, **cap_kwargs)

    assert (result['status'], result['error'], result['hash_id']) == ('error', 'raw_input_empty', hash_id)
    assert _record(hash_id) == before


def test_a_partly_truncated_body_still_carries_text_and_updates(plan_context):
    """⛔ MATCHED CONTROL — a positive cap that clips the body keeps text, so the update proceeds."""
    hash_id = _stored()

    result = _update(hash_id, _NEW_BODY, raw_input_max_bytes=8)

    assert result['outcome'] == 'updated'
    assert _record(hash_id)['raw_input']['body'] == _NEW_BODY[:8] + _findings_core.RAW_INPUT_TRUNCATION_MARKER
