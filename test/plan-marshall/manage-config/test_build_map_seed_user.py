# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_config_build_map_seed_fixtures import (
    Namespace,
    _cmd_build_map_mod,
    _cmd_init_mod,
    _patch_aggregate,
    json,
)


def test_user_correction_survives_reseed_and_wins_at_read(plan_context, monkeypatch):
    """A direct correction to build.map survives a re-seed and wins at read."""
    # seed, then correct an entry directly on the seeded block.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    config['build']['map']['python'][0]['build_class'] = 'none'
    marshal_path.write_text(json.dumps(config, indent=2), encoding='utf-8')

    # re-seed (write-once preserves the corrected seed), then read.
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))
    read_result = _cmd_build_map_mod.cmd_build_map_read(Namespace(verb='read'))

    # correction survived re-seed and wins at read
    persisted = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert persisted['build']['map']['python'][0]['build_class'] == 'none'
    assert read_result['status'] == 'success'
    merged_python = {e['glob']: e for e in read_result['build_map']['python']}
    assert merged_python['scripts/*.py']['build_class'] == 'none'
