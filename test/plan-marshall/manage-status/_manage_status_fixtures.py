#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage-status`` test modules.

Holds the definitions used by modules of MORE THAN ONE unit in this
directory. A definition used by one unit belongs in that unit's own
helper; this file is for what genuinely crosses them.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import get_script_path


def _age_token(plan_context, plan_id: str, seconds: int) -> None:
    """Backdate the stored token's ``set_at`` by ``seconds``, in place.

    Staleness is a READ-side property of ``set_at``, so the only way to observe
    it is to move the stamp rather than to wait. Both the lifecycle unit and the
    ownership-invariant unit need that, which is what puts it here.
    """
    status_file = plan_context.plan_dir_for(plan_id) / 'status.json'
    status = json.loads(status_file.read_text(encoding='utf-8'))
    aged = datetime.now(UTC) - timedelta(seconds=seconds)
    status['title_token']['set_at'] = aged.strftime('%Y-%m-%dT%H:%M:%SZ')
    status_file.write_text(json.dumps(status), encoding='utf-8')


def _write_status(plan_dir: Path) -> None:
    """Create ``{plan_dir}/status.json`` with no phases and no metadata.

    The consumers need the plan to EXIST rather than to hold anything: each
    seeds this empty document and asserts on what the command under test makes
    of it. The pre-split copy said "so ``--persist`` write paths can read it",
    which was true of the one module it came from and is not true of the three
    that share it now.
    """
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': {}}),
        encoding='utf-8',
    )


SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
