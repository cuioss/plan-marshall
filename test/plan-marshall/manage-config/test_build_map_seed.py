# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_build_map_seed.py: merge."""

#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_config_build_map_seed_fixtures import _FAKE_AGGREGATED, _config_core_mod, pytest

# =============================================================================
# Pure read/merge logic (no extension discovery)
# =============================================================================


def test_merge_build_map_returns_seed_from_build_block():
    """merge_build_map returns a deep copy of build.map unchanged."""
    # build_map lives under the top-level build block (relocated).
    config = {'build': {'map': _FAKE_AGGREGATED}}

    merged = _config_core_mod.merge_build_map(config)

    # same structure, deep-copied (mutating result must not touch config)
    assert merged == _FAKE_AGGREGATED
    merged['python'][0]['build_class'] = 'mutated'
    assert config['build']['map']['python'][0]['build_class'] == 'compile'


def test_merge_build_map_fails_closed_when_build_map_absent():
    """merge_build_map raises BuildMapMissingError when build.map is absent.

    There is no override layer and no silent empty-dict fallback — a missing seed
    surfaces as a structured error (fail-closed) instead of a silent no-build.
    """
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map({})


def test_merge_build_map_fails_closed_when_build_block_lacks_map():
    """A build block without a map key still fails closed."""
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map({'build': {'other': {}}})


@pytest.mark.parametrize(
    'corrupt_build_map', [[], ['glob'], 'a string', 42, {'python': None}, {'python': 'not a list'}]
)
def test_merge_build_map_fails_closed_when_build_map_is_non_dict(corrupt_build_map):
    """A present-but-corrupt build.map raises BuildMapMissingError.

    Regression: merge_build_map previously assigned build['map'] to
    seed without a type check, so a corrupt non-dict value crashed the subsequent
    .items() deep-copy with an untyped AttributeError. Partially corrupt dicts
    (e.g. {'python': None} or {'python': 'not a list'}) also crash the inner list
    comprehension with an untyped TypeError. The hardened fail-closed guard now
    treats all corrupt build_map shapes the same as an absent one.
    """
    config = {'build': {'map': corrupt_build_map}}
    with pytest.raises(_config_core_mod.BuildMapMissingError):
        _config_core_mod.merge_build_map(config)
