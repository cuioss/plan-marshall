#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import json


def _seed_plan_local_lane(plan_context, plan_id: str, overrides: dict[str, dict]) -> None:
    """Write the plan-local declaration channel: ``status.metadata.finalize_step_overrides``."""
    status_path = plan_context.plan_dir_for(plan_id) / 'status.json'
    status_path.write_text(
        json.dumps({'metadata': {'finalize_step_overrides': overrides}}, indent=2),
        encoding='utf-8',
    )
