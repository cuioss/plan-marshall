#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unchanged Q-Gate re-emission keeps the recorded resolution.

Parametrized over every non-pending member of ``VALID_RESOLUTIONS`` — derived
from the constant, so a newly-added resolution earns a row rather than a silent
pass: resolve, re-add identically, and read back the same resolution, detail
and timestamp with the pending count unchanged. A changed detail, file or rule
still files a new pending record (the identity rule is unchanged).
"""

import _findings_core
import pytest
from _findings_store_fixtures import (
    QGATE_PERSIST_OK,
    add_qgate_finding,
    query_qgate_findings,
    resolve_qgate_finding,
)

from conftest import load_script_module

_constants = load_script_module('plan-marshall', 'tools-file-ops', 'constants.py', '_tools_file_ops_constants_qgate')

#: Every resolution an unchanged re-emission must keep — the full
#: ``VALID_RESOLUTIONS`` vocabulary minus the pending value a fresh record
#: already carries, and minus ``taken_into_account``. The review's own
#: "superseded by a later round" disposition is NOT an operator decision: a
#: re-filed blocking finding must return to pending, which
#: ``test_a_refiled_taken_into_account_record_is_rearmed`` pins. Derived, never
#: restated, so the parametrization cannot drift behind the validator's accept set.
_TAKEN_INTO_ACCOUNT = _constants.RESOLUTION_TAKEN_INTO_ACCOUNT
_NON_PENDING_RESOLUTIONS = tuple(
    resolution
    for resolution in _constants.VALID_RESOLUTIONS
    if resolution not in (_constants.RESOLUTION_PENDING, _TAKEN_INTO_ACCOUNT)
)

assert _NON_PENDING_RESOLUTIONS, 'the derived resolution population is empty'

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = tuple(f'qe-survives-{resolution}' for resolution in _NON_PENDING_RESOLUTIONS) + (
    'qe-survives-changed-content',
    'qe-survives-taken-into-account',
)


@pytest.mark.parametrize('resolution', _NON_PENDING_RESOLUTIONS)
def test_unchanged_reemission_keeps_recorded_resolution(plan_context, resolution):
    """Resolve to ``resolution``, re-add byte-identically, and read everything back."""
    plan_id = f'qe-survives-{resolution}'
    first = add_qgate_finding(
        plan_id,
        '5-execute',
        'qgate',
        'test-failure',
        'Survives re-emission',
        'Unchanged detail',
        file_path='src/kept.py',
        rule='kept-rule',
    )
    assert first['status'] == 'success'

    resolved = resolve_qgate_finding(plan_id, '5-execute', first['hash_id'], resolution, 'Decided by the operator')
    assert resolved['status'] == 'success'
    before = query_qgate_findings(plan_id, '5-execute')['findings'][0]

    second = add_qgate_finding(
        plan_id,
        '5-execute',
        'qgate',
        'test-failure',
        'Survives re-emission',
        'Unchanged detail',
        file_path='src/kept.py',
        rule='kept-rule',
    )

    assert second['status'] == 'kept'
    assert second['status'] in QGATE_PERSIST_OK
    assert second['hash_id'] == first['hash_id']
    assert second['resolution'] == resolution

    after = query_qgate_findings(plan_id, '5-execute')['findings'][0]
    assert after['resolution'] == resolution
    assert after['detail'] == before['detail']
    assert after['timestamp'] == before['timestamp']
    assert after['resolution_timestamp'] == before['resolution_timestamp']

    pending = query_qgate_findings(plan_id, '5-execute', resolution='pending')
    assert pending['filtered_count'] == 0


def test_a_refiled_taken_into_account_record_is_rearmed(plan_context):
    """The review's rule-keyed supersession is not an operator decision: a re-file re-arms it.

    ``taken_into_account`` is what a full loop-back round records through its rule key
    for a finding it superseded (``resolution_source: rule``). A review that re-files
    the identical finding is reporting that it still blocks, so the record is pending
    again and an operator close can accept it. An operator ``accepted`` record, and a
    triage Hold resolved through ``resolve_qgate_finding``, are kept — the latter is
    pinned by ``test_lb118_reobservation_d3``.
    """
    plan_id = 'qe-survives-taken-into-account'
    first = add_qgate_finding(
        plan_id,
        '5-execute',
        'qgate',
        'test-failure',
        'Re-armed finding',
        'Unchanged detail',
        file_path='src/rearmed.py',
        rule='rearmed-rule',
    )
    assert first['status'] == 'success'
    _findings_core.resolve_qgate_findings_by_rule(
        plan_id, '5-execute', 'rearmed-rule', _TAKEN_INTO_ACCOUNT, 'Superseded by the next round'
    )

    second = add_qgate_finding(
        plan_id,
        '5-execute',
        'qgate',
        'test-failure',
        'Re-armed finding',
        'Unchanged detail',
        file_path='src/rearmed.py',
        rule='rearmed-rule',
    )

    assert second['status'] == 'reopened'
    assert second['previous_resolution'] == _TAKEN_INTO_ACCOUNT
    assert second['reopened_by'] == 'observation'
    assert query_qgate_findings(plan_id, '5-execute', resolution='pending')['filtered_count'] == 1


def test_changed_content_files_fresh_pending(plan_context):
    """The identity rule is unchanged: a changed detail files a new pending record."""
    plan_id = 'qe-survives-changed-content'
    first = add_qgate_finding(
        plan_id,
        '5-execute',
        'qgate',
        'test-failure',
        'Drifting finding',
        'Version one',
    )
    resolve_qgate_finding(plan_id, '5-execute', first['hash_id'], 'accepted', 'Seen before')

    second = add_qgate_finding(
        plan_id,
        '5-execute',
        'qgate',
        'test-failure',
        'Drifting finding',
        'Version two',
    )

    assert second['status'] == 'success'
    assert second['hash_id'] != first['hash_id']
    assert query_qgate_findings(plan_id, '5-execute', resolution='pending')['filtered_count'] == 1
