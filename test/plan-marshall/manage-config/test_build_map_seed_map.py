# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import (
    _FAKE_AGGREGATED,
    Namespace,
    _cmd_build_map_mod,
    _cmd_init_mod,
    _patch_aggregate,
    json,
)

# =============================================================================
# Seed write-once semantics (handler path)
# =============================================================================


def test_build_map_seed_writes_aggregated_structure_under_build_block(plan_context, monkeypatch):
    """build-map seed writes the aggregated {domain: [...]} structure under build.map.

    Init no longer seeds build_map, so a bare init leaves the block absent; the
    first explicit seed against the deterministic fake is the authoritative write.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)

    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # handler reports a seed action and the persisted block matches
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'
    assert result['domain_count'] == 1

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    # build_map is relocated under the top-level build block — NOT under skill_domains.
    assert config['build']['map'] == _FAKE_AGGREGATED
    assert 'build_map' not in config.get('skill_domains', {})


def test_build_map_seed_is_write_once(plan_context, monkeypatch):
    """A re-seed preserves an existing seed (write-once) — never clobbers it."""
    # first seed writes the fake map (init no longer pre-seeds)
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    first = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    assert first['action'] == 'seeded'

    # Mutate the persisted seed to emulate a user correction (directly on the
    # seeded entries — there is no separate override layer).
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build']['map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # re-seed
    second = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # re-seed preserved the user correction, did not clobber
    assert second['action'] == 'preserved'
    after = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert after['build']['map']['python'][0]['build_class'] == 'none'


def test_build_map_read_returns_seed(plan_context, monkeypatch):
    """build-map read returns the seed from build.map unchanged."""
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    assert result['status'] == 'success'
    assert result['build_map'] == _FAKE_AGGREGATED
    assert result['domain_count'] == 1


def test_build_map_read_fails_closed_when_seed_absent(plan_context):
    """build-map read returns a structured error when build.map is absent.

    Init no longer seeds the block, so a bare init already leaves build_map absent
    — read must fail closed without any pre-read stripping.
    """
    # bare init leaves the config without a build.map block.
    _cmd_init_mod.cmd_init(Namespace(force=False))

    result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # fail-closed surfaces as a structured error, not an empty success.
    assert result['status'] == 'error'
    assert 'build.map' in result['error']
