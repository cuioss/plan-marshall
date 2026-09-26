# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_validate_loadable_fixtures import _mem

# =============================================================================
# Helper-level invariants — pin _is_external_step / _resolve_standards_path
# =============================================================================


class TestHelperInvariants:
    def test_is_external_step_classifies_correctly(self):
        assert _mem._is_external_step('project:foo') is True
        assert _mem._is_external_step('plan-marshall:plan-retrospective') is True
        assert _mem._is_external_step('push') is False
        assert _mem._is_external_step('default:push') is False

    def test_resolve_standards_path_strips_default_prefix(self):
        bare_path = _mem._resolve_standards_path('push')
        prefixed_path = _mem._resolve_standards_path('default:push')
        assert bare_path == prefixed_path

    def test_resolve_standards_path_lands_under_phase_6_finalize_standards(self):
        path = _mem._resolve_standards_path('push')
        assert path.parent.name == 'standards'
        assert path.parent.parent.name == 'phase-6-finalize'
