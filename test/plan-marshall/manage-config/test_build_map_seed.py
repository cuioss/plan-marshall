#!/usr/bin/env python3
"""Tests for the marshal.json build_map seed, override layer, and write-once semantics.

Covers Deliverable 3 of the build-map plan:
- build-map seed writes the aggregated {domain: [{glob, role, build_class}]} structure.
- A user override in build_map_overrides survives a re-seed and wins by glob at read.
- Write-once: a re-seed never clobbers an existing seed.
- The merge logic (seed ∪ overrides) is a pure function of the config dict.
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


_cmd_build_map_mod = _load_module('_cmd_build_map_for_build_map_test', '_cmd_build_map.py')
_cmd_init_mod = _load_module('_cmd_init_for_build_map_test', '_cmd_init.py')

# Resolve the SAME _config_core module the handler imported its helpers from, so
# patching aggregate_build_map there is what seed_build_map_into() actually sees.
# (_cmd_build_map does `from _config_core import seed_build_map_into`, binding the
# function to that module's globals — not to any importlib-renamed copy.)
_config_core_mod = sys.modules[_cmd_build_map_mod.seed_build_map_into.__module__]


# A deterministic fake aggregation result so the seed tests do not depend on the
# live extension set. Mirrors the real {domain: [{glob, role, build_class}]} shape.
_FAKE_AGGREGATED = {
    'python': [
        {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'prod-compile'},
        {'glob': 'test/**/*.py', 'role': 'test', 'build_class': 'test-run'},
    ],
    'documentation': [
        {'glob': '*.adoc', 'role': 'documentation', 'build_class': 'docs-validate'},
    ],
}


def _patch_aggregate(monkeypatch):
    """Patch aggregate_build_map on the _config_core module the handler resolves
    against, so seed_build_map_into() consumes the deterministic fake."""
    monkeypatch.setattr(_config_core_mod, 'aggregate_build_map', lambda: _FAKE_AGGREGATED)


# =============================================================================
# Pure merge logic (no extension discovery)
# =============================================================================


def test_merge_build_map_returns_seed_when_no_overrides():
    """merge_build_map returns the seed unchanged when build_map_overrides is absent."""
    # Arrange
    config = {'build_map': _FAKE_AGGREGATED}

    # Act
    merged = _config_core_mod.merge_build_map(config)

    # Assert — same structure, deep-copied (mutating result must not touch config)
    assert merged == _FAKE_AGGREGATED
    merged['python'][0]['build_class'] = 'mutated'
    assert config['build_map']['python'][0]['build_class'] == 'prod-compile'


def test_merge_build_map_override_wins_by_glob():
    """An override entry replaces the seed entry sharing the same glob."""
    # Arrange — override the prod-compile build_class to none for the scripts glob
    config = {
        'build_map': _FAKE_AGGREGATED,
        'build_map_overrides': [
            {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'none'},
        ],
    }

    # Act
    merged = _config_core_mod.merge_build_map(config)

    # Assert — the python production entry now reads build_class none; test entry untouched
    python_entries = {e['glob']: e for e in merged['python']}
    assert python_entries['scripts/*.py']['build_class'] == 'none'
    assert python_entries['test/**/*.py']['build_class'] == 'test-run'


def test_merge_build_map_unmatched_override_appended_under_overrides_domain():
    """An override whose glob is absent from the seed is preserved under _overrides."""
    # Arrange
    config = {
        'build_map': _FAKE_AGGREGATED,
        'build_map_overrides': [
            {'glob': 'generated/*.py', 'role': 'production', 'build_class': 'none'},
        ],
    }

    # Act
    merged = _config_core_mod.merge_build_map(config)

    # Assert — the unmatched override is not silently dropped
    assert '_overrides' in merged
    assert merged['_overrides'] == [
        {'glob': 'generated/*.py', 'role': 'production', 'build_class': 'none'}
    ]


def test_merge_build_map_empty_when_no_build_map():
    """merge_build_map returns an empty dict when the config has no build_map."""
    assert _config_core_mod.merge_build_map({}) == {}


# =============================================================================
# Seed write-once semantics (handler path)
# =============================================================================


def test_build_map_seed_writes_aggregated_structure(plan_context, monkeypatch):
    """build-map seed writes the aggregated {domain: [...]} structure into marshal.json."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)

    # Act
    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — handler reports a seed action and the persisted block matches
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'
    assert result['domain_count'] == 2

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert config['build_map'] == _FAKE_AGGREGATED


def test_build_map_seed_is_write_once(plan_context, monkeypatch):
    """A re-seed preserves an existing seed (write-once) — never clobbers it."""
    # Arrange — first seed writes the fake map
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    first = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    assert first['action'] == 'seeded'

    # Mutate the persisted seed to emulate a user correction
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build_map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act — re-seed
    second = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — re-seed preserved the user correction, did not clobber
    assert second['action'] == 'preserved'
    after = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert after['build_map']['python'][0]['build_class'] == 'none'


def test_user_override_survives_reseed_and_wins_at_read(plan_context, monkeypatch):
    """A build_map_overrides entry survives a re-seed and wins by glob at read."""
    # Arrange — seed, then add a user override directly to marshal.json
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build_map_overrides'] = [
        {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'none'},
    ]
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act — re-seed (write-once preserves seed AND leaves overrides untouched), then read
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    read_result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert — override survived re-seed and wins at read
    persisted = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert persisted['build_map_overrides'] == [
        {'glob': 'scripts/*.py', 'role': 'production', 'build_class': 'none'}
    ]
    assert read_result['status'] == 'success'
    merged_python = {e['glob']: e for e in read_result['build_map']['python']}
    assert merged_python['scripts/*.py']['build_class'] == 'none'


def test_build_map_read_returns_seed_when_no_overrides(plan_context, monkeypatch):
    """build-map read returns the seed unchanged when no overrides are present."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Act
    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert
    assert result['status'] == 'success'
    assert result['build_map'] == _FAKE_AGGREGATED
    assert result['domain_count'] == 2
