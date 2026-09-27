#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import Path, json


def _read_task(plans_root: Path, plan_id: str, number: int) -> dict:
    task_path = plans_root / plan_id / 'tasks' / f'TASK-{number:03d}.json'
    data: dict = json.loads(task_path.read_text(encoding='utf-8'))
    return data
