#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import json


def _write_execution_profile(plan_context, plan_id, profile):
    """Seed ``{plan_dir}/status.json`` with ``metadata.execution_profile``."""
    plan_dir = plan_context.plan_dir_for(plan_id)
    (plan_dir / 'status.json').write_text(
        json.dumps({'plan_id': plan_id, 'metadata': {'execution_profile': profile}}, indent=2),
        encoding='utf-8',
    )
