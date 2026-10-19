#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The integrity record is serialized with the status writers, and its keys are reserved.

Three behaviours:

* ``record_integrity`` waits for the status writer's critical section instead of
  writing straight through it;
* ``manage-status metadata --set`` / ``--set --append`` refuses the three keys
  only their owning verb may write;
* the owning verbs still write them: the criteria freeze records
  ``snapshot_frozen`` and ``loop-back close`` records the override head.
"""

from __future__ import annotations

import json
import threading
from argparse import Namespace
from pathlib import Path

import _criteria_snapshot as _snap
from _locks_core import rmw_json

from conftest import load_script_module

PLAN_ID = 'lb74-status-integrity-d3'

_lifecycle = load_script_module('plan-marshall', 'manage-status', '_cmd_lifecycle.py', '_lb74_d3_lifecycle')
_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_lb74_d3_query')

PROTECTED = ('criteria_integrity', 'snapshot_frozen', 'functional_review_override_heads')


def _plan(plan_context) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    status = {'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {'use_worktree': False}}
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution: lock\n\n## Deliverables\n\n### 1. Deliver it\n\n'
        '**Affected files:**\n- `src/x.py` (write-new)\n\n**Success Criteria:**\n- it works\n',
        encoding='utf-8',
    )
    return plan_dir


def _metadata(plan_dir: Path) -> dict:
    return json.loads((plan_dir / 'status.json').read_text(encoding='utf-8')).get('metadata') or {}


def test_record_integrity_waits_for_the_status_guard(plan_context) -> None:
    plan_dir = _plan(plan_context)
    status_path = plan_dir / 'status.json'
    entered = threading.Event()
    release = threading.Event()
    outcome: dict[str, bool] = {}

    def _hold(current: dict) -> dict:
        entered.set()
        release.wait(10)
        return current

    def _record() -> None:
        outcome['result'] = _snap.record_integrity(PLAN_ID, snapshot_frozen=True)

    # Hold the REAL status-writer critical section: rmw_json is the seam write_status commits through.
    holder = threading.Thread(target=lambda: rmw_json(status_path, _hold))
    holder.start()
    assert entered.wait(5)
    worker = threading.Thread(target=_record)
    worker.start()
    worker.join(0.3)
    assert worker.is_alive(), 'record_integrity wrote through the held status guard'
    assert _snap.integrity_record(PLAN_ID) == {}

    release.set()
    holder.join(10)
    worker.join(10)
    assert not worker.is_alive()
    assert outcome['result'] is True
    assert _snap.integrity_record(PLAN_ID)['snapshot_frozen'] is True


def test_metadata_set_refuses_every_protected_key(plan_context) -> None:
    plan_dir = _plan(plan_context)

    for field in PROTECTED:
        result = _query.cmd_metadata(Namespace(plan_id=PLAN_ID, set=True, get=False, field=field, value='forged'))
        assert result['status'] == 'error', (field, result)
        assert result['error'] == 'protected_metadata_key'
        assert field not in _metadata(plan_dir)


def test_metadata_append_refuses_every_protected_key(plan_context) -> None:
    plan_dir = _plan(plan_context)

    for field in PROTECTED:
        result = _query.cmd_metadata(
            Namespace(plan_id=PLAN_ID, set=True, get=False, append=True, field=field, value='forged')
        )
        assert result['status'] == 'error', (field, result)
        assert result['error'] == 'protected_metadata_key'
        assert field not in _metadata(plan_dir)


def test_metadata_set_still_writes_an_unprotected_key(plan_context) -> None:
    plan_dir = _plan(plan_context)

    result = _query.cmd_metadata(Namespace(plan_id=PLAN_ID, set=True, get=False, field='change_type', value='feature'))

    assert result['status'] == 'success', result
    assert _metadata(plan_dir)['change_type'] == 'feature'


def test_the_criteria_freeze_still_records_snapshot_frozen(plan_context) -> None:
    _plan(plan_context)

    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    assert _snap.integrity_record(PLAN_ID)['snapshot_frozen'] is True
