# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_classify_paths_via_extensions_fixtures import _resolved_role


def test_infrastructure_config_render_target_wins_by_delegation():
    """A CI-workflow render target delegates to the infra-config predicate."""
    assert _resolved_role('.github/workflows/ci.yml.template') == 'config'
