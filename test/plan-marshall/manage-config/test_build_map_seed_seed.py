# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_config_build_map_seed_fixtures import (
    Namespace,
    _cmd_build_map_mod,
    _cmd_init_mod,
    _LiveAndDeadRouteExtension,
    _patch_aggregate,
    _PythonRouteExtension,
    _wire_real_aggregator,
    json,
)

# =============================================================================
# Regression: relocation + retired-key removal
# =============================================================================


def test_seed_never_writes_retired_override_keys(plan_context, monkeypatch):
    """No retired build_map_overrides key is written by the seed path.

    The override layer was dropped: the build_map under the top-level build block
    is the single source of truth, and user corrections are made directly to the
    seeded entries. The build_map cluster no longer carries any activation_globs of
    its own — pre-push activation derives from the build_map's per-entry globs.
    """
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # the retired override key never appears anywhere in the persisted config.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'build_map_overrides' not in config
    assert 'build_map_overrides' not in config.get('build', {})
    # The build_map cluster under build carries no activation_globs key —
    # activation derives from the per-entry globs, not a separate cluster list.
    # (The unrelated plan.phase-6-finalize.pre_push_quality_gate.activation_globs
    # field is a distinct knob and is NOT covered by this assertion.)
    assert 'activation_globs' not in config['build']
    build_map = config['build']['map']
    assert 'activation_globs' not in build_map


def test_seed_cli_persists_route_for_out_of_scripts_glob(plan_context, monkeypatch):
    """The seed CLI persists the out-of-scripts route under build.map.

    End-to-end through the seed handler (cmd_build_map_seed): init, then seed
    against an extension declaring an out-of-scripts production route. The
    persisted build.map must carry a python-domain glob matching
    that file. Init no longer pre-seeds, so the seed writes the derived block.
    """
    # init, wire the real aggregator against an extension declaring an
    # out-of-scripts production route.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _wire_real_aggregator(monkeypatch, _PythonRouteExtension())

    # seed through the CLI handler.
    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed'))

    # handler seeded, and the persisted block carries the matching glob.
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    build_map = config['build']['map']
    assert 'python' in build_map
    prod_globs = [e['glob'] for e in build_map['python'] if e['role'] == 'production']

    import fnmatch

    assert any(fnmatch.fnmatchcase('marketplace/targets/generate.py', g) for g in prod_globs), (
        f'seeded build_map missing a glob for the out-of-scripts file; globs={prod_globs}'
    )


def test_seed_persists_live_glob_and_prunes_dead_glob(plan_context, monkeypatch):
    """End-to-end: the seeded build.map carries the live glob and NOT the dead glob.

    Genuine regression coverage for the build-map-seed-prune-dead-globs fix: against
    the unfixed deriver the dead ``vendor/*.tsx`` route would survive into the
    persisted build.map; with D1's tree-presence filter it is pruned at seed time.
    The fixture tree carries only the live route's file, so the dead route matches
    nothing and must be absent from the output.
    """
    # init, then wire the real aggregator over a tracked tree that
    # carries the LIVE route's file but no file for the DEAD route.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _wire_real_aggregator(
        monkeypatch,
        _LiveAndDeadRouteExtension(),
        tracked_files=['marketplace/targets/generate.py'],
    )

    # seed through the real CLI pipeline.
    result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))
    assert result['status'] == 'success'
    assert result['action'] == 'seeded'

    # the persisted build.map carries ONLY the live glob; the dead glob is absent.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    build_map = config['build']['map']
    assert 'python' in build_map
    globs = [entry['glob'] for entry in build_map['python']]
    assert 'marketplace/targets/*.py' in globs, f'live glob was pruned; globs={globs}'
    assert 'vendor/*.tsx' not in globs, f'dead glob leaked into seeded build.map; globs={globs}'
