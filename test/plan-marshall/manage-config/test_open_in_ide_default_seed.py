#!/usr/bin/env python3
"""Test that `manage-config init` seeds plan.open_in_ide=true.

Guards the marshall-steward seed contract: a fresh marshal.json produced by
`manage-config init` (the wizard entry point) carries the open-in-ide flag
as a flat boolean at `plan.open_in_ide` and NOT as a top-level peer of
`system` / `plan` / `skill_domains`.
"""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

from conftest import PlanContext

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_cmd_init_mod = _load_module('_cmd_init_seed_test', '_cmd_init.py')
cmd_init = _cmd_init_mod.cmd_init


def test_init_seeds_open_in_ide_true_under_plan_namespace():
    """Fresh marshal.json must contain plan.open_in_ide = True (flat bool)."""
    # Arrange
    with PlanContext(plan_id='seed-open-in-ide') as ctx:
        # Act
        result = cmd_init(Namespace(force=False))

        # Assert
        assert result['status'] == 'success'
        marshal_path = ctx.fixture_dir / 'marshal.json'
        assert marshal_path.exists()

        config = json.loads(marshal_path.read_text(encoding='utf-8'))

        # Flat boolean under `plan`; not a top-level alias, not a sub-dict.
        assert 'open_in_ide' not in config, (
            "open_in_ide must NOT be a top-level key — it lives under `plan`."
        )
        assert 'plan' in config
        assert 'open_in_ide' in config['plan'], (
            'plan.open_in_ide must be seeded by manage-config init'
        )
        assert config['plan']['open_in_ide'] is True
