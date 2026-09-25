# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import Namespace, _cmd_init_mod, json

# =============================================================================
# Init-seed removal — init / get_default_config() no longer seed build_map
# =============================================================================
#
# The premature init-time auto-seed was removed: build_map is materialised only at
# wizard Step 8b (build-map seed) after architecture discovery, so the
# applicability filter has discovered modules to scope against. A bare init must
# leave the build.map block absent.


def test_fresh_init_does_not_seed_build_map(plan_context):
    """`manage-config init` no longer seeds build.map.

    Regression for the seed-ordering fix: init runs before architecture discovery,
    so it must NOT seed the (applicability-scoped) build_map. The block is absent
    after a bare init and is materialised later at wizard Step 8b.
    """
    # fresh init.
    _cmd_init_mod.cmd_init(Namespace(force=False))

    # the build.map block is absent after a bare init.
    marshal_path = plan_context.fixture_dir / 'marshal.json'
    config = json.loads(marshal_path.read_text(encoding='utf-8'))
    assert 'map' not in config.get('build', {}), (
        'init must NOT seed build.map (seeded at Step 8b after architecture discovery)'
    )
