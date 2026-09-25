# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_orchestrator_ledger_fixtures import (
    _header,
    _ledger,
    _row,
    json,
    root,
)

# =============================================================================
# mutate_row — per-row isolation
# =============================================================================


class TestMutateRow:
    def test_should_mutate_one_row_and_leave_every_other_row_byte_identical(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1), _row('PLAN-02', 'second', seq=2)))
        other = _ledger.row_path(root, 'PLAN-02')
        other_before = other.read_bytes()
        header_before = _ledger.header_path(root).read_bytes()

        def _transition(row: dict) -> str:
            previous = str(row['status'])
            row['status'] = 'running'
            return previous

        outcome = _ledger.mutate_row(root, 'PLAN-01', _transition)

        assert outcome == {'result': 'staged'}
        assert json.loads(_ledger.row_path(root, 'PLAN-01').read_text(encoding='utf-8'))['status'] == 'running'
        assert other.read_bytes() == other_before
        assert _ledger.header_path(root).read_bytes() == header_before

    def test_should_report_available_plans_for_an_absent_row(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-02', 'second', seq=1),))

        outcome = _ledger.mutate_row(root, 'PLAN-09', lambda row: None)

        assert outcome == {'available_plans': ['PLAN-02']}
        assert not _ledger.row_path(root, 'PLAN-09').exists()

    def test_should_refuse_an_unreadable_row_and_leave_it_untouched(self, root):
        _ledger.write_layout(root, _header(), '', ())
        path = _ledger.row_path(root, 'PLAN-01')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('<<<<<<< HEAD\n', encoding='utf-8')

        outcome = _ledger.mutate_row(root, 'PLAN-01', lambda row: row.update(status='running'))

        assert set(outcome) == {'unreadable'}
        assert path.read_text(encoding='utf-8') == '<<<<<<< HEAD\n'

    def test_should_refuse_an_id_outside_the_grammar(self, root):
        assert _ledger.mutate_row(root, '../x', lambda row: None) == {'invalid_id': '../x'}
