#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The protected metadata keys are exactly the keys a verb writes there.

``snapshot_frozen`` is an inner key of the ``criteria_integrity`` block, so no
verb writes it at the top level of ``metadata`` and protecting that name guards a
write that never happens. The two remaining keys each have an owning verb.
"""

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from typing import Any

import _criteria_snapshot as _snap

from conftest import load_script_module

PLAN_ID = 'lb77-protected-keys-d3'

_query = load_script_module('plan-marshall', 'manage-status', '_status_query.py', '_lb77_d3_query')


def _plan(plan_context: Any) -> Path:
    plan_dir = Path(plan_context.plan_dir_for(PLAN_ID))
    status = {'title': 'fixture', 'phases': [], 'current_phase': '6-finalize', 'metadata': {'use_worktree': False}}
    (plan_dir / 'status.json').write_text(json.dumps(status), encoding='utf-8')
    (plan_dir / 'solution_outline.md').write_text(
        '# Solution: keys\n\n## Deliverables\n\n### 1. Deliver it\n\n'
        '**Affected files:**\n- `src/x.py` (write-new)\n\n**Success Criteria:**\n- it works\n',
        encoding='utf-8',
    )
    return plan_dir


def _metadata(plan_dir: Path) -> dict:
    return json.loads((plan_dir / 'status.json').read_text(encoding='utf-8')).get('metadata') or {}


def test_the_protected_set_is_exactly_the_keys_a_verb_writes() -> None:
    assert _query.PROTECTED_METADATA_FIELDS == frozenset({_snap.INTEGRITY_KEY, _snap.OVERRIDE_HEADS_KEY})
    assert _snap.SNAPSHOT_FROZEN_KEY not in _query.PROTECTED_METADATA_FIELDS


def test_a_top_level_snapshot_frozen_write_cannot_forge_the_integrity_block(plan_context) -> None:
    plan_dir = _plan(plan_context)
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    result = _query.cmd_metadata(
        Namespace(plan_id=PLAN_ID, set=True, get=False, append=False, field=_snap.SNAPSHOT_FROZEN_KEY, value='false')
    )

    assert result['status'] == 'success', result
    assert _metadata(plan_dir)[_snap.SNAPSHOT_FROZEN_KEY] == 'false'
    assert _snap.integrity_record(PLAN_ID)[_snap.SNAPSHOT_FROZEN_KEY] is True
