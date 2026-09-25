# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import Namespace, _cmd_build_map_mod, _cmd_init_mod, _patch_aggregate


def test_default_seed_without_force_preserves_existing_block(plan_context, monkeypatch):
    """`seed` without `--force` still preserves an existing block (write-once).

    The negative control for the force path: with an existing block, a default
    seed (force=False) reports action: preserved and leaves the block untouched.
    """
    # seed once so a block exists.
    _cmd_init_mod.cmd_init(Namespace(force=False))
    _patch_aggregate(monkeypatch)
    _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))

    # re-seed without force.
    second = _cmd_build_map_mod.cmd_build_map_seed(Namespace(verb='seed', force=False))

    # preserved, not re-derived.
    assert second['action'] == 'preserved'
