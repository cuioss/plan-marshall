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
# Force reseed — `build-map seed --force` clears and re-derives
# =============================================================================
#
# The default seed is write-once; `--force` is the explicit clear-and-re-derive
# escape hatch (the meta-project migration path). A forced reseed reports
# action: re-derived (distinct from seeded / preserved) and overwrites any
# existing block, including a user correction.


def test_force_reseed_clears_and_rederives_existing_block(plan_context, monkeypatch):
    """`seed --force` over an existing block clears and re-derives it.

    With a build_map already present, a default seed would preserve it; `--force`
    bypasses the write-once guard and re-derives the block from the current
    aggregation, reporting action: re-derived.
    """
    # seed once (deterministic fake), so a block already exists.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    first = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))
    assert first['action'] == 'seeded'

    # forced reseed.
    forced = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=True))

    # re-derived (not preserved), and the persisted block matches the
    # current aggregation.
    assert forced['status'] == 'success'
    assert forced['action'] == 're-derived'
    assert forced['domain_count'] == 1

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert config['build']['map'] == _FAKE_AGGREGATED


def test_force_reseed_overwrites_user_correction(plan_context, monkeypatch):
    """A user correction is overwritten by `--force` (NOT write-once).

    The default seed preserves a hand-edited entry, but `--force` is the documented
    migration escape hatch: it discards stale or hand-edited entries and re-derives
    a clean block from the current aggregation.
    """
    # seed, then hand-edit an entry directly on the seeded block.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build']['map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # forced reseed.
    forced = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=True))

    # the correction was overwritten by the re-derived aggregation.
    assert forced['action'] == 're-derived'
    after = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert after['build']['map']['python'][0]['build_class'] == 'compile'
