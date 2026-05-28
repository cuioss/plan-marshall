#!/usr/bin/env python3
"""Test default-config schema additions for the split-gate / default-base-branch plan.

Covers:
- `DEFAULT_PLAN_FINALIZE` includes `auto_merge_after_ci` with default `False`.
- A fresh marshal.json carries `project.default_base_branch == 'main'`.
- The new `project` CLI noun round-trips a custom `default_base_branch`.
"""

# ruff: noqa: I001, E402

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-config'
    / 'scripts'
)

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


_config_defaults_mod = _load_module(
    '_config_defaults_for_split_gate_test', '_config_defaults.py'
)
_cmd_init_mod = _load_module(
    '_cmd_init_for_split_gate_test', '_cmd_init.py'
)
_cmd_system_plan_mod = _load_module(
    '_cmd_system_plan_for_split_gate_test', '_cmd_system_plan.py'
)


def test_default_plan_finalize_includes_auto_merge_after_ci():
    """DEFAULT_PLAN_FINALIZE must declare auto_merge_after_ci with conservative default False."""
    # Arrange
    finalize_defaults = _config_defaults_mod.DEFAULT_PLAN_FINALIZE

    # Act / Assert
    assert 'auto_merge_after_ci' in finalize_defaults, (
        'auto_merge_after_ci must be schema-registered in DEFAULT_PLAN_FINALIZE'
    )
    assert finalize_defaults['auto_merge_after_ci'] is False, (
        'auto_merge_after_ci default must be False (conservative; prompt on every merge)'
    )


def test_default_project_default_base_branch_is_main():
    """DEFAULT_PROJECT must declare default_base_branch == 'main'."""
    # Arrange
    project_defaults = _config_defaults_mod.DEFAULT_PROJECT

    # Act / Assert
    assert 'default_base_branch' in project_defaults
    assert project_defaults['default_base_branch'] == 'main'


def test_get_default_config_includes_project_block():
    """get_default_config() must include the 'project' block with default_base_branch == 'main'."""
    # Arrange / Act
    config = _config_defaults_mod.get_default_config()

    # Assert
    assert 'project' in config
    assert config['project'].get('default_base_branch') == 'main'


def test_fresh_marshal_seeds_project_default_base_branch_main(plan_context):
    """`manage-config init` against a fresh fixture must seed project.default_base_branch=main."""
    # Arrange / Act
    result = _cmd_init_mod.cmd_init(Namespace(force=False))

    # Assert
    assert result['status'] == 'success'
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    assert marshal_path.exists()

    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'project' in config
    assert config['project'].get('default_base_branch') == 'main'


def test_project_set_then_get_roundtrip_default_base_branch(plan_context):
    """`project set --field default_base_branch --value develop` must round-trip via get."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Act — set
    set_args = Namespace(verb='set', field='default_base_branch', value='develop')
    set_result = _cmd_system_plan_mod.cmd_project(set_args)
    assert set_result['status'] == 'success'

    # Act — get
    get_args = Namespace(verb='get', field='default_base_branch')
    get_result = _cmd_system_plan_mod.cmd_project(get_args)

    # Assert
    assert get_result['status'] == 'success'
    assert get_result['value'] == 'develop'


def test_project_get_returns_default_when_block_absent(plan_context):
    """A fresh marshal.json without the `project` block returns DEFAULT_PROJECT values."""
    # Arrange — initialize then remove `project` block to emulate legacy schema
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.pop('project', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act
    args = Namespace(verb='get', field='default_base_branch')
    result = _cmd_system_plan_mod.cmd_project(args)

    # Assert — implicit-default semantics mirror open_in_ide / DEFAULT_PLAN_* blocks
    assert result['status'] == 'success'
    assert result['value'] == 'main'
