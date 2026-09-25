#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import _FAKE_AGGREGATED, _config_core_mod


def _patch_aggregate(monkeypatch):
    """Patch aggregate_build_map on the _config_core module the handler resolves
    against, so seed_build_map_into() consumes the deterministic fake."""
    monkeypatch.setattr(_config_core_mod, 'aggregate_build_map', lambda: _FAKE_AGGREGATED)
