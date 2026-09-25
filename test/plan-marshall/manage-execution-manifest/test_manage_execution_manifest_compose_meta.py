# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import (
    _apply_lane_resolution,
    _patch_element_lane,
)


def test_meta_project_minimal_keeps_derived_state_without_override(monkeypatch):
    """Meta-project invariant: a minimal posture keeps derived-state by default (never SILENTLY dropped)."""
    _patch_element_lane(monkeypatch)
    kept, dropped, warnings = _apply_lane_resolution(['project:finalize-step-deploy-target'], 'minimal', None)

    assert kept == ['project:finalize-step-deploy-target']
    assert dropped == []
    assert warnings == []
