#!/usr/bin/env python3
"""Tests for the marshal.json build_map seed under skill_domains (D6/D7/D8/D14).

Covers the relocated, required build_map cluster:
- build-map seed writes the aggregated {domain: [{glob, role, build_class}]}
  structure under ``skill_domains.build_map`` (relocated from the top level).
- Write-once: a re-seed never clobbers an existing seed, so a user correction
  made directly to the seeded entries survives.
- merge_build_map reads from ``skill_domains.build_map`` and fails closed
  (raises) when the block is absent — there is no override layer.
- Regression: ``skill_domains.build_map`` is present after seed, and the retired
  ``build_map_overrides`` / ``activation_globs`` keys are never written.
"""

# ruff: noqa: I001, E402

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

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


def _strip_init_seeded_build_map(fixture_dir: Path) -> None:
    """Remove the build_map that ``cmd_init`` auto-seeds via get_default_config().

    ``cmd_init`` now always seeds ``skill_domains.build_map`` (D6) from the live
    extension set. Tests that drive the write-once seed path with a deterministic
    fake must first clear that init-seeded block, otherwise the write-once guard
    short-circuits to ``preserved`` against the real (empty/live) aggregation.
    """
    marshal_path = fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.get('skill_domains', {}).pop('build_map', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')


# =============================================================================
# Pure read/merge logic (no extension discovery)
# =============================================================================


def test_merge_build_map_returns_seed_from_skill_domains():
    """merge_build_map returns a deep copy of skill_domains.build_map unchanged."""
    # Arrange — build_map lives under skill_domains (relocated).
    config = {'skill_domains': {'build_map': _FAKE_AGGREGATED}}

    # Act
    merged = _config_core_mod.merge_build_map(config)

    # Assert — same structure, deep-copied (mutating result must not touch config)
    assert merged == _FAKE_AGGREGATED
    merged['python'][0]['build_class'] = 'mutated'
    assert config['skill_domains']['build_map']['python'][0]['build_class'] == 'prod-compile'


def test_merge_build_map_fails_closed_when_build_map_absent():
    """merge_build_map raises BuildMapMissingError when skill_domains.build_map is absent.

    There is no override layer and no silent empty-dict fallback — a missing seed
    surfaces as a structured error (fail-closed) instead of a silent no-build.
    """
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map({})


def test_merge_build_map_fails_closed_when_skill_domains_lacks_build_map():
    """A skill_domains block without a build_map key still fails closed."""
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map({'skill_domains': {'system': {}}})


@pytest.mark.parametrize('corrupt_build_map', [[], ['glob'], 'a string', 42])
def test_merge_build_map_fails_closed_when_build_map_is_non_dict(corrupt_build_map):
    """A present-but-non-dict skill_domains.build_map raises BuildMapMissingError.

    Regression: merge_build_map previously assigned skill_domains['build_map'] to
    seed without a type check, so a corrupt non-dict value crashed the subsequent
    .items() deep-copy with an untyped AttributeError. The hardened fail-closed
    guard now treats a non-dict build_map the same as an absent one.
    """
    config = {'skill_domains': {'build_map': corrupt_build_map}}
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map(config)


def test_get_build_map_returns_empty_when_absent():
    """get_build_map returns {} (not an error) when skill_domains.build_map is absent."""
    assert _config_core_mod.get_build_map({}) == {}
    assert _config_core_mod.get_build_map({'skill_domains': {}}) == {}


def test_get_build_map_returns_relocated_block():
    """get_build_map locates the relocated build_map under skill_domains."""
    config = {'skill_domains': {'build_map': _FAKE_AGGREGATED}}
    assert _config_core_mod.get_build_map(config) == _FAKE_AGGREGATED


# =============================================================================
# Seed write-once semantics (handler path)
# =============================================================================


def test_build_map_seed_writes_aggregated_structure_under_skill_domains(plan_context, monkeypatch):
    """build-map seed writes the aggregated {domain: [...]} structure under skill_domains."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _strip_init_seeded_build_map(plan_context.fixture_dir)
    _patch_aggregate(monkeypatch)

    # Act
    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — handler reports a seed action and the persisted block matches
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'
    assert result['domain_count'] == 2

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    # build_map is relocated under skill_domains — NOT at the top level.
    assert config['skill_domains']['build_map'] == _FAKE_AGGREGATED
    assert 'build_map' not in config


def test_build_map_seed_is_write_once(plan_context, monkeypatch):
    """A re-seed preserves an existing seed (write-once) — never clobbers it."""
    # Arrange — first seed writes the fake map
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _strip_init_seeded_build_map(plan_context.fixture_dir)
    _patch_aggregate(monkeypatch)
    first = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    assert first['action'] == 'seeded'

    # Mutate the persisted seed to emulate a user correction (directly on the
    # seeded entries — there is no separate override layer).
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['skill_domains']['build_map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act — re-seed
    second = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — re-seed preserved the user correction, did not clobber
    assert second['action'] == 'preserved'
    after = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert after['skill_domains']['build_map']['python'][0]['build_class'] == 'none'


def test_user_correction_survives_reseed_and_wins_at_read(plan_context, monkeypatch):
    """A direct correction to skill_domains.build_map survives a re-seed and wins at read."""
    # Arrange — seed, then correct an entry directly on the seeded block.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _strip_init_seeded_build_map(plan_context.fixture_dir)
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['skill_domains']['build_map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act — re-seed (write-once preserves the corrected seed), then read.
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    read_result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert — correction survived re-seed and wins at read
    persisted = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert persisted['skill_domains']['build_map']['python'][0]['build_class'] == 'none'
    assert read_result['status'] == 'success'
    merged_python = {e['glob']: e for e in read_result['build_map']['python']}
    assert merged_python['scripts/*.py']['build_class'] == 'none'


def test_build_map_read_returns_seed(plan_context, monkeypatch):
    """build-map read returns the seed from skill_domains.build_map unchanged."""
    # Arrange
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _strip_init_seeded_build_map(plan_context.fixture_dir)
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Act
    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert
    assert result['status'] == 'success'
    assert result['build_map'] == _FAKE_AGGREGATED
    assert result['domain_count'] == 2


def test_build_map_read_fails_closed_when_seed_absent(plan_context):
    """build-map read returns a structured error when skill_domains.build_map is absent.

    A fresh init seeds the (live-aggregated) build_map, so to exercise the
    fail-closed path the test strips the block before reading.
    """
    # Arrange — init, then remove the seeded build_map to emulate a corrupt config.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config.get('skill_domains', {}).pop('build_map', None)
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # Act
    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # Assert — fail-closed surfaces as a structured error, not an empty success.
    assert result['status'] == 'error'
    assert 'build_map' in result['error']


# =============================================================================
# Regression: relocation + retired-key removal (D6/D7/D14)
# =============================================================================


def test_fresh_init_seeds_required_build_map_under_skill_domains(plan_context):
    """`manage-config init` always seeds the required skill_domains.build_map block."""
    # Arrange / Act — fresh init (live aggregation; may be empty but must be present).
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # Assert — the build_map key is present under skill_domains and required.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'skill_domains' in config
    assert 'build_map' in config['skill_domains'], (
        'skill_domains.build_map must be seeded (required) on init'
    )
    assert isinstance(config['skill_domains']['build_map'], dict)


def test_seed_never_writes_retired_override_keys(plan_context, monkeypatch):
    """No retired build_map_overrides key is written by the seed path.

    The override layer was dropped (D14): the build_map under skill_domains is the
    single source of truth, and user corrections are made directly to the seeded
    entries. The build_map cluster no longer carries any activation_globs of its
    own — pre-push activation derives from the build_map's per-entry globs (D7/D8).
    """
    # Arrange / Act
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # Assert — the retired override key never appears anywhere in the persisted config.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'build_map_overrides' not in config
    assert 'build_map_overrides' not in config.get('skill_domains', {})
    # The build_map cluster under skill_domains carries no activation_globs key —
    # activation derives from the per-entry globs, not a separate cluster list.
    # (The unrelated plan.phase-6-finalize.pre_push_quality_gate.activation_globs
    # field is a distinct knob and is NOT covered by this assertion.)
    assert 'activation_globs' not in config['skill_domains']
    build_map = config['skill_domains']['build_map']
    assert 'activation_globs' not in build_map
