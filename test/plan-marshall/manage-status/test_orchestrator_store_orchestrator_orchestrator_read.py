# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_orchestrator_store_orchestrator_fixtures import (
    Namespace,
    _create_args,
    _orchestrator_queue_dir,
    _orchestrator_root,
    _row,
    _seed_ledger,
    cmd_orchestrator_create,
    cmd_orchestrator_read,
)

# =============================================================================
# Read
# =============================================================================


class TestOrchestratorRead:
    def test_should_read_created_ledger_as_assembled_document(self, plan_context):
        cmd_orchestrator_create(_create_args('read-epic'))

        result = cmd_orchestrator_read(Namespace(plan_id='read-epic'))

        assert result['status'] == 'success'
        assert result['store'] == 'orchestrator'
        assert result['plan']['kind'] == 'orchestrator'
        assert result['plan']['phase'] == 'init'
        assert result['plan']['plans'] == []
        assert result['plan']['resume_anchor'] == ''
        assert 'unreadable_rows' not in result

    def test_should_assemble_rows_in_seq_order(self, plan_context):
        root = _orchestrator_root(plan_context, 'order-epic')
        _seed_ledger(
            root,
            anchor='next: analyze PLAN-02',
            rows=(_row('PLAN-02', 'second', seq=1), _row('PLAN-01', 'first', seq=2)),
        )

        result = cmd_orchestrator_read(Namespace(plan_id='order-epic'))

        assert [row['id'] for row in result['plan']['plans']] == ['PLAN-02', 'PLAN-01']
        assert result['plan']['resume_anchor'] == 'next: analyze PLAN-02'

    def test_should_report_file_not_found_for_missing_status(self, plan_context):
        result = cmd_orchestrator_read(Namespace(plan_id='absent-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'file_not_found'

    def test_should_report_unreadable_row_instead_of_dropping_it(self, plan_context):
        root = _orchestrator_root(plan_context, 'bad-row-epic')
        _seed_ledger(root, rows=(_row('PLAN-01', 'first'),))
        (_orchestrator_queue_dir(plan_context, 'bad-row-epic') / 'PLAN-02.json').write_text(
            '<<<<<<< HEAD\n', encoding='utf-8'
        )

        result = cmd_orchestrator_read(Namespace(plan_id='bad-row-epic'))

        assert result['status'] == 'success'
        assert [row['id'] for row in result['plan']['plans']] == ['PLAN-01']
        assert [row['file'] for row in result['unreadable_rows']] == ['PLAN-02.json']

    def test_should_report_unreadable_header_distinctly_from_absent(self, plan_context):
        root = _orchestrator_root(plan_context, 'bad-header-epic')
        root.mkdir(parents=True)
        (root / 'status.json').write_text('[1, 2]', encoding='utf-8')

        result = cmd_orchestrator_read(Namespace(plan_id='bad-header-epic'))

        assert result['status'] == 'error'
        assert result['error'] == 'header_unreadable'
