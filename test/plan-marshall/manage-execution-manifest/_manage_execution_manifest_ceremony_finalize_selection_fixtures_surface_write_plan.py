#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_ceremony_finalize_selection_fixtures import _IMMUNE_OFF_LANE_BLOCKS, _mem


def _patch_immune_off_lanes(monkeypatch):
    """Monkeypatch ``_resolve_element_lane`` to the canned immune-off blocks."""
    monkeypatch.setattr(_mem, '_resolve_element_lane', lambda step: _IMMUNE_OFF_LANE_BLOCKS.get(step))
