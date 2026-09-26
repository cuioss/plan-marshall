# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_execution_manifest_validate_loadable_fixtures import (
    DEFAULT_PHASE_6_STEPS,
    _compose_ns,
    _mem,
    _validate_loadable_ns,
    cmd_compose,
    cmd_validate_loadable,
)

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
