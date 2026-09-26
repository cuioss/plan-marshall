# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_validate_loadable.py: single."""

from _manage_execution_manifest_validate_loadable_fixtures import _validate_loadable_ns, cmd_validate_loadable

# =============================================================================
# Single-step form
# =============================================================================


class TestSingleStepForm:
    def test_built_in_step_with_present_standards_returns_loadable(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-builtin-ok', step_id='push'))
        assert result is not None
        assert result['status'] == 'success'
        assert result['step_id'] == 'push'
        assert result['loadable'] is True
        assert result['standards_path'].endswith('phase-6-finalize/standards/push.md')
        # Happy path carries no `message` field.
        assert 'message' not in result

    def test_default_prefix_is_stripped(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-prefix', step_id='default:push'))
        assert result is not None
        assert result['loadable'] is True
        assert result['step_id'] == 'push', 'default: prefix must be stripped from echoed step_id'

    def test_missing_standards_file_returns_actionable_message(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-missing', step_id='ghost-step-that-does-not-exist'))
        assert result is not None
        assert result['status'] == 'success'
        assert result['loadable'] is False
        # Canonical actionable phrasing — phase-6-finalize Step 1.5 surfaces this verbatim.
        assert 'ghost-step-that-does-not-exist' in result['message']
        assert 'missing standards file' in result['message']
        assert 'deleted the file without sweeping' in result['message']
        assert result['standards_path'].endswith('phase-6-finalize/workflow/ghost-step-that-does-not-exist.md')

    def test_project_step_short_circuits_to_loadable(self, plan_context):
        """External steps (project:foo) are not validated by this guard."""
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-project', step_id='project:finalize-step-deploy-target')
        )
        assert result is not None
        assert result['loadable'] is True
        assert result['standards_path'] == ''
        # External step ids are echoed verbatim (no prefix stripping).
        assert result['step_id'] == 'project:finalize-step-deploy-target'

    def test_skill_step_short_circuits_to_loadable(self, plan_context):
        """Fully-qualified skill steps short-circuit the same way as project: steps."""
        result = cmd_validate_loadable(_validate_loadable_ns('vl-skill', step_id='plan-marshall:plan-retrospective'))
        assert result is not None
        assert result['loadable'] is True
        assert result['standards_path'] == ''
