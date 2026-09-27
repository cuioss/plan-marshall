# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_orchestrator_store_orchestrator.py: orchestrator create."""

from _manage_status_orchestrator_store_orchestrator_fixtures import (
    _create_args,
    _orchestrator_anchor_file,
    _orchestrator_queue_dir,
    _orchestrator_root,
    _read_header,
    _row,
    _seed_ledger,
    cmd_orchestrator_create,
)

# =============================================================================
# Create
# =============================================================================


class TestOrchestratorCreate:
    def test_should_create_header_and_empty_anchor(self, plan_context):
        result = cmd_orchestrator_create(_create_args('test-epic'))

        assert result['status'] == 'success'
        assert result['store'] == 'orchestrator'
        header = _read_header(plan_context, 'test-epic')
        assert header['kind'] == 'orchestrator'
        assert header['title'] == 'Test Epic'
        assert header['phase'] == 'init'
        assert header['workstreams'] == []
        assert header['metadata'] == {}
        assert 'created' in header
        # The header carries no queue, no anchor and no shared `updated` stamp.
        assert 'plans' not in header
        assert 'resume_anchor' not in header
        assert 'updated' not in header
        assert _orchestrator_anchor_file(plan_context, 'test-epic').read_text(encoding='utf-8') == '\n'
        assert not _orchestrator_queue_dir(plan_context, 'test-epic').exists()

    def test_should_reject_duplicate_create_without_force(self, plan_context):
        cmd_orchestrator_create(_create_args('dup-epic'))

        result = cmd_orchestrator_create(_create_args('dup-epic', title='Second'))

        assert result['status'] == 'error'
        assert result['error'] == 'already_exists'

    def test_should_overwrite_header_with_force_and_leave_queue_untouched(self, plan_context):
        root = _orchestrator_root(plan_context, 'force-epic')
        _seed_ledger(root, header={'title': 'Original'}, rows=(_row('PLAN-01', 'first'),))
        row_file = _orchestrator_queue_dir(plan_context, 'force-epic') / 'PLAN-01.json'
        row_bytes = row_file.read_bytes()

        result = cmd_orchestrator_create(_create_args('force-epic', title='Replaced', force=True))

        assert result['status'] == 'success'
        assert _read_header(plan_context, 'force-epic')['title'] == 'Replaced'
        assert row_file.read_bytes() == row_bytes
