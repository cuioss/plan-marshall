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

import _cmd_loop_back as _loop_back
import _criteria_snapshot as _snap

from conftest import load_script_module

PLAN_ID = 'lb77-protected-keys-d3'
HEAD = 'a' * 40

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


def test_the_protected_set_is_exactly_the_keys_a_verb_writes_at_top_level(plan_context) -> None:
    """Derived from what the owning verbs actually write, not from a pinned literal.

    Each protected key has an owner that writes it at the TOP level of
    ``status.metadata``; ``snapshot_frozen`` is an inner key of the
    ``criteria_integrity`` block, so no verb writes it there. The test runs the two
    owners and compares the guard's set with the keys that appeared: a key added to
    the guard with no owning writer fails it. (An owner added with no guard entry is
    NOT covered here — the candidate set below is what bounds the comparison.)
    """
    plan_dir = _plan(plan_context)
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'
    changed, error = _loop_back._record_override_head(PLAN_ID, _loop_back.FUNCTIONAL_REVIEW_STEP, HEAD)
    assert (changed, error) == (True, None)

    metadata = _metadata(plan_dir)
    candidates = {_snap.INTEGRITY_KEY, _snap.OVERRIDE_HEADS_KEY, _snap.SNAPSHOT_FROZEN_KEY}
    written_at_top_level = candidates & set(metadata)

    assert written_at_top_level == {_snap.INTEGRITY_KEY, _snap.OVERRIDE_HEADS_KEY}
    assert _query.PROTECTED_METADATA_FIELDS == written_at_top_level


def test_a_top_level_snapshot_frozen_write_cannot_forge_the_integrity_block(plan_context) -> None:
    plan_dir = _plan(plan_context)
    assert _snap.write_snapshot(PLAN_ID)['status'] == 'success'

    result = _query.cmd_metadata(
        Namespace(plan_id=PLAN_ID, set=True, get=False, append=False, field=_snap.SNAPSHOT_FROZEN_KEY, value='false')
    )

    assert result['status'] == 'success', result
    assert _metadata(plan_dir)[_snap.SNAPSHOT_FROZEN_KEY] == 'false'
    assert _snap.integrity_record(PLAN_ID)[_snap.SNAPSHOT_FROZEN_KEY] is True
