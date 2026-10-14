#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Unchanged Q-Gate re-emission keeps the recorded resolution.

Parametrized over every non-pending member of ``VALID_RESOLUTIONS`` — derived
from the constant, so a newly-added resolution earns a row rather than a silent
pass: resolve, re-add identically, and read back the same resolution, detail
and timestamp with the pending count unchanged. A changed detail, file or rule
still files a new pending record (the identity rule is unchanged).
"""

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
#: already carries. Derived, never restated, so the parametrization cannot
#: drift behind the validator's accept set.
_NON_PENDING_RESOLUTIONS = tuple(
    resolution for resolution in _constants.VALID_RESOLUTIONS if resolution != _constants.RESOLUTION_PENDING
)

# Plan ids this module's tests file findings against — seeded by the autouse
# ``_materialize_declared_plan_dirs`` fixture in ``test/conftest.py``.
PLAN_IDS = tuple(f'qe-survives-{resolution}' for resolution in _NON_PENDING_RESOLUTIONS) + (
    'qe-survives-changed-content',
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
