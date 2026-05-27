#!/usr/bin/env python3
"""Tests for the manage-execution-manifest ``validate-loadable`` subcommand.

Covers the loadability fail-fast guard consumed by phase-6-finalize Step 1.5:

- Single-step happy path (built-in step with present standards file)
- Single-step missing-file path (canonical actionable message)
- External step short-circuit (project: / bundle:skill → loadable=true, no check)
- ``default:`` prefix is accepted and stripped
- ``--all`` happy path against a real manifest
- ``--all`` reports per-step results and unloadable_count when one entry is missing
- Mutual-exclusivity + missing-mode validation errors
- Manifest-missing yields ``file_not_found`` for ``--all``
"""

# ruff: noqa: I001, E402

import importlib.util
from argparse import Namespace
from pathlib import Path


# Tier 2 direct import — match the test layout used by sibling tests.
_SCRIPTS_DIR = (
    Path(__file__).parent.parent.parent.parent
    / 'marketplace'
    / 'bundles'
    / 'plan-marshall'
    / 'skills'
    / 'manage-execution-manifest'
    / 'scripts'
)


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _SCRIPTS_DIR / filename)
    assert spec is not None
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


_mem = _load_module('_mem_validate_loadable', 'manage-execution-manifest.py')
cmd_compose = _mem.cmd_compose
cmd_validate_loadable = _mem.cmd_validate_loadable
DEFAULT_PHASE_5_STEPS = _mem.DEFAULT_PHASE_5_STEPS
DEFAULT_PHASE_6_STEPS = _mem.DEFAULT_PHASE_6_STEPS

# Silence the best-effort decision-log subprocess so tests do not depend on a
# running executor.
_mem._log_decision = lambda *a, **kw: None  # type: ignore[attr-defined]


# =============================================================================
# Namespace helpers
# =============================================================================


def _validate_loadable_ns(
    plan_id: str = 'vl-test',
    step_id: str | None = None,
    use_all: bool = False,
) -> Namespace:
    return Namespace(plan_id=plan_id, step_id=step_id, all=use_all)


def _compose_ns(
    plan_id: str,
    phase_6_steps: str | None = None,
    change_type: str = 'feature',
    scope_estimate: str = 'multi_module',
    affected_files_count: int = 5,
) -> Namespace:
    return Namespace(
        plan_id=plan_id,
        change_type=change_type,
        track='complex',
        scope_estimate=scope_estimate,
        recipe_key=None,
        affected_files_count=affected_files_count,
        phase_5_steps=','.join(DEFAULT_PHASE_5_STEPS),
        phase_6_steps=phase_6_steps if phase_6_steps is not None else ','.join(DEFAULT_PHASE_6_STEPS),
        commit_strategy=None,
    )


# =============================================================================
# Single-step form
# =============================================================================


class TestSingleStepForm:
    def test_built_in_step_with_present_standards_returns_loadable(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-builtin-ok', step_id='commit-push'))
        assert result is not None
        assert result['status'] == 'success'
        assert result['step_id'] == 'commit-push'
        assert result['loadable'] is True
        assert result['standards_path'].endswith('phase-6-finalize/standards/commit-push.md')
        # Happy path carries no `message` field.
        assert 'message' not in result

    def test_default_prefix_is_stripped(self, plan_context):
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-prefix', step_id='default:commit-push')
        )
        assert result is not None
        assert result['loadable'] is True
        assert result['step_id'] == 'commit-push', 'default: prefix must be stripped from echoed step_id'

    def test_missing_standards_file_returns_actionable_message(self, plan_context):
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-missing', step_id='ghost-step-that-does-not-exist')
        )
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
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-skill', step_id='plan-marshall:plan-retrospective')
        )
        assert result is not None
        assert result['loadable'] is True
        assert result['standards_path'] == ''


# =============================================================================
# Mutual exclusivity
# =============================================================================


class TestArgumentValidation:
    def test_neither_step_id_nor_all_returns_invalid_arguments(self, plan_context):
        result = cmd_validate_loadable(_validate_loadable_ns('vl-neither'))
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'

    def test_both_step_id_and_all_returns_invalid_arguments(self, plan_context):
        result = cmd_validate_loadable(
            _validate_loadable_ns('vl-both', step_id='commit-push', use_all=True)
        )
        assert result is not None
        assert result['status'] == 'error'
        assert result['error'] == 'invalid_arguments'


# =============================================================================
# Bulk (--all) form
# =============================================================================


class TestBulkForm:
    def test_all_against_default_manifest_reports_every_step(self, plan_context):
        cmd_compose(_compose_ns('vl-all-default'))
        result = cmd_validate_loadable(_validate_loadable_ns('vl-all-default', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 0
        results = result['results']
        assert isinstance(results, list)
        assert len(results) == len(DEFAULT_PHASE_6_STEPS)
        for entry in results:
            assert entry['loadable'] is True
            assert entry['step_id'] in DEFAULT_PHASE_6_STEPS

    def test_all_flags_unloadable_step_with_actionable_message(self, plan_context):
        # Compose a manifest then mutate it to add a non-existent step. The
        # composer's candidate-set normalization strips unknown names, so we
        # have to write the manifest directly (re-use the file ops the script
        # itself uses).
        cmd_compose(_compose_ns('vl-all-missing'))
        manifest = _mem.read_manifest('vl-all-missing')
        assert manifest is not None
        manifest['phase_6']['steps'].append('ghost-step-not-on-disk')
        _mem.write_manifest('vl-all-missing', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-all-missing', use_all=True))
        assert result is not None
        assert result['status'] == 'success'
        assert result['unloadable_count'] == 1
        unloadable = [r for r in result['results'] if not r['loadable']]
        assert len(unloadable) == 1
        ghost = unloadable[0]
        assert ghost['step_id'] == 'ghost-step-not-on-disk'
        assert 'missing standards file' in ghost['message']
        assert 'ghost-step-not-on-disk' in ghost['message']

    def test_all_with_external_steps_marks_them_loadable_without_check(self, plan_context):
        # Compose a default manifest, then inject an external step.
        cmd_compose(_compose_ns('vl-all-mixed'))
        manifest = _mem.read_manifest('vl-all-mixed')
        assert manifest is not None
        manifest['phase_6']['steps'].insert(1, 'project:finalize-step-deploy-target')
        _mem.write_manifest('vl-all-mixed', manifest)

        result = cmd_validate_loadable(_validate_loadable_ns('vl-all-mixed', use_all=True))
        assert result is not None
        assert result['unloadable_count'] == 0
        external_rows = [r for r in result['results'] if ':' in r['step_id']]
        assert len(external_rows) == 1
        assert external_rows[0]['loadable'] is True
        assert external_rows[0]['standards_path'] == ''

    def test_all_with_missing_manifest_returns_file_not_found(self, plan_context, capsys):
        # Do not compose — manifest does not exist on disk.
        result = cmd_validate_loadable(_validate_loadable_ns('vl-no-manifest', use_all=True))
        # cmd_validate_loadable returns None on file_not_found and emits a
        # TOON error to stdout via output_toon_error. Confirm via captured stdout.
        assert result is None
        captured = capsys.readouterr()
        assert 'file_not_found' in captured.out


# =============================================================================
# Helper-level invariants — pin _is_external_step / _resolve_standards_path
# =============================================================================


class TestHelperInvariants:
    def test_is_external_step_classifies_correctly(self):
        assert _mem._is_external_step('project:foo') is True
        assert _mem._is_external_step('plan-marshall:plan-retrospective') is True
        assert _mem._is_external_step('commit-push') is False
        assert _mem._is_external_step('default:commit-push') is False

    def test_resolve_standards_path_strips_default_prefix(self):
        bare_path = _mem._resolve_standards_path('commit-push')
        prefixed_path = _mem._resolve_standards_path('default:commit-push')
        assert bare_path == prefixed_path

    def test_resolve_standards_path_lands_under_phase_6_finalize_standards(self):
        path = _mem._resolve_standards_path('commit-push')
        assert path.parent.name == 'standards'
        assert path.parent.parent.name == 'phase-6-finalize'
