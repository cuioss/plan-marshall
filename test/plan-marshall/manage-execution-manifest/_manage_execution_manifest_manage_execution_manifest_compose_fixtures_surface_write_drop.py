#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_manage_execution_manifest_compose_fixtures import _LANE_BLOCKS, _mem


def _patch_element_lane(monkeypatch, blocks=None):
    """Monkeypatch ``_resolve_element_lane`` to return canned blocks per step id."""
    table = _LANE_BLOCKS if blocks is None else blocks
    monkeypatch.setattr(_mem, '_resolve_element_lane', lambda step: table.get(step))
