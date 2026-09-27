#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import Namespace, _cmd_build_map_mod, _cmd_init_mod, _config_core_mod


def _seed_with(monkeypatch, aggregation):
    """Init + seed marshal.json with a specific deterministic aggregation.

    Patches aggregate_build_map on the _config_core module the seed handler
    resolves against, then drives cmd_build_map_seed so the persisted build.map
    reflects `aggregation`.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    monkeypatch.setattr(_config_core_mod, 'aggregate_build_map', lambda: aggregation)
    seed = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))
    assert seed['action'] == 'seeded'
