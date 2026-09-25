# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import (
    ROLE_CONFIG,
    Namespace,
    _cmd_build_map_mod,
    _cmd_init_mod,
    _MultiModuleSubdirConfigExtension,
    _wire_real_aggregator,
    extension_base,
    json,
)


def test_e2e_multi_module_subdir_only_config_seeds_and_builds(plan_context, monkeypatch):
    """End-to-end: a subdir-only config seeds a route AND drives a build verdict.

    Pipeline regression pinning the bare-basename subdir-matching fix across the
    full seed → build.map → build-decision flow:

    1. SEED — wire the real aggregator over a multi-module git fixture whose only
       ``package.json`` files live in subdirectories (``module-a/``, ``module-b/``).
       Seed through ``cmd_build_map_seed``. The bare-basename ``package.json`` route
       must survive the tree-presence prune and be persisted under ``build.map``.
    2. BUILD-DECISION — run the real ``should_execute_build`` (reading the seeded
       globs back from the SAME persisted marshal.json) against a footprint that
       touches a subdirectory-only ``package.json``. It must return ``build``.
    """
    # Arrange — init, then wire the real aggregator over a multi-module fixture
    # tree carrying package.json ONLY in subdirectories (never at repo root).
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _wire_real_aggregator(
        monkeypatch,
        _MultiModuleSubdirConfigExtension(),
        tracked_files=['module-a/package.json', 'module-b/package.json'],
    )

    # Act 1 — seed through the real CLI pipeline.
    seed_result = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))

    # Assert 1 — the bare-basename config route survived the prune and persisted.
    assert seed_result['status'] == 'success'
    assert seed_result['action'] == 'seeded'

    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    build_map = config['build']['map']
    assert 'node' in build_map, f'subdir-only config domain dropped from seed; build_map={build_map}'
    config_globs = [entry['glob'] for entry in build_map['node'] if entry['role'] == ROLE_CONFIG]
    assert 'package.json' in config_globs, (
        f'bare-basename subdir-only config route was pruned at seed time; globs={config_globs}'
    )

    # Act 2 — drive the real build-decision over a subdir-only config footprint.
    # The seed leg pointed get_marshal_path() at the git fixture tree via
    # PLAN_TRACKED_CONFIG_DIR; drop it so _read_build_map_globs resolves
    # get_marshal_path() back through PLAN_BASE_DIR to the SAME plan_context
    # marshal.json the seed just wrote — making the build-decision read the
    # persisted build.map for real.
    monkeypatch.delenv('PLAN_TRACKED_CONFIG_DIR', raising=False)
    # Only the footprint helper is redirected; _read_build_map_globs reads the
    # seeded build.map back from the persisted marshal.json for real.
    monkeypatch.setattr(extension_base, '_resolve_plan_footprint', lambda _plan: ['module-a/package.json'])
    verdict = extension_base.should_execute_build('verify', plan_context.plan_id)

    # Assert 2 — the seeded subdir-only config route matches the subdir footprint
    # and forces a build (not_necessary would be the unfixed regression).
    assert verdict['decision'] == 'build', f'subdir-only config change did not trigger a build; verdict={verdict}'
    assert verdict['canonical_command'] == 'verify'
