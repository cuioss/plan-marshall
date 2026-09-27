#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import read_manifest


def _manifest_phase_6_steps(result: dict) -> list[str]:
    """Read the persisted manifest after a successful compose; return phase_6.steps."""
    plan_id = result['plan_id']
    manifest = read_manifest(plan_id)
    assert manifest is not None
    return list(manifest.get('phase_6', {}).get('steps', []))
