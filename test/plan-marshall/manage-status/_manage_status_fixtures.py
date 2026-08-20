#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""Shared preamble for the ``manage-status`` test modules.

Holds the definitions used by modules of MORE THAN ONE unit in this
directory. A definition used by one unit belongs in that unit's own
helper; this file is for what genuinely crosses them.
"""

from __future__ import annotations

import json
from pathlib import Path

from conftest import get_script_path


def _write_status(plan_dir: Path) -> None:
    plan_dir.mkdir(parents=True, exist_ok=True)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_dir.name, 'phases': [], 'metadata': {}}),
        encoding='utf-8',
    )


SCRIPT_PATH = get_script_path('plan-marshall', 'manage-status', 'manage-status.py')
