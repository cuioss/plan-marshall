# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _SUBTRACTION_RECORD_FIELDS,
    _compose_ns,
    cmd_compose,
)


def test_compose_result_exposes_every_subtraction_record_field(plan_context):
    """Each subtraction-record field is present and carries the shared shape."""
    result = cmd_compose(_compose_ns(plan_id='subtraction-fields'))

    assert result is not None and result['status'] == 'success'
    for field in _SUBTRACTION_RECORD_FIELDS:
        assert field in result, f'{field} must be surfaced on the compose result'
        assert isinstance(result[field], list)
        for record in result[field]:
            assert set(record) == {'step', 'reason'}, f'{field} record has the wrong shape: {record!r}'
            assert record['step'] and record['reason']


def test_compose_result_drops_the_retired_self_review_key(plan_context):
    """The always-``False`` ``pre_submission_self_review_omitted`` key is gone.

    A clean break, not a shim: the key reported the outcome of a pre-filter that
    structurally never fired, so every consumer that read it read a constant.
    """
    result = cmd_compose(_compose_ns(plan_id='subtraction-nokey'))

    assert result is not None
    assert 'pre_submission_self_review_omitted' not in result


def test_compose_result_drops_the_retired_commit_push_scalar(plan_context):
    """``commit_push_omitted`` is replaced by, not duplicated alongside, the records.

    Keeping both would be the two-sources-of-truth shape the record list exists to
    remove — a scalar that can drift out of step with the drops it summarises.
    """
    result = cmd_compose(_compose_ns(plan_id='subtraction-noscalar', commit_and_push='false'))

    assert result is not None
    assert 'commit_push_omitted' not in result
    assert result['commit_push_dropped']
