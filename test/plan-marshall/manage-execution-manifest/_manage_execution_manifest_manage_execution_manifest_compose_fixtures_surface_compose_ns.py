#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import json

# =============================================================================
# Recipe / lesson provenance from status metadata (recipe→default drift fix)
# =============================================================================


def _write_status_metadata(plan_context, plan_id: str, metadata: dict) -> None:
    """Seed ``{plan_dir}/status.json`` with the given ``metadata`` block."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': metadata}, indent=2),
        encoding='utf-8',
    )
