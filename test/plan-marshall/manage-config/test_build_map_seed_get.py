# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import _FAKE_AGGREGATED, _config_core_mod, _config_defaults_mod


def test_get_build_map_returns_empty_when_absent():
    """get_build_map returns {} (not an error) when build.map is absent."""
    assert _config_core_mod.get_build_map({}) == {}
    assert _config_core_mod.get_build_map({'build': {}}) == {}



def test_get_build_map_returns_relocated_block():
    """get_build_map locates the relocated build_map under the top-level build block."""
    config = {'build': {'map': _FAKE_AGGREGATED}}
    assert _config_core_mod.get_build_map(config) == _FAKE_AGGREGATED



def test_get_default_config_has_skill_domains_without_build_map():
    """get_default_config() returns skill_domains present but build.map absent.

    The default config no longer ships a build_map block — get_default_config()
    must return skill_domains (with at least the system domain) and no build.map
    block.
    """
    config = _config_defaults_mod.get_default_config()

    # skill_domains present, build.map absent.
    assert 'skill_domains' in config
    assert 'system' in config['skill_domains']
    assert 'map' not in config.get('build', {})
