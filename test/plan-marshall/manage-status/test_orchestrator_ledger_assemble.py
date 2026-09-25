# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_orchestrator_ledger_fixtures import (
    _header,
    _ledger,
    _row,
    pytest,
    root,
)

# =============================================================================
# The assembled view
# =============================================================================


class TestAssembleView:
    def test_should_round_trip_header_anchor_and_rows(self, root):
        rows = (_row('PLAN-01', 'first', seq=1), _row('PLAN-02', 'second', seq=2))
        _ledger.write_layout(root, _header(), 'await PR #9 CI', rows)

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert view.queue_state == _ledger.QUEUE_PRESENT
        assert view.unreadable_rows == ()
        assert list(view.document) == list(_ledger.VIEW_FIELDS)
        assert view.document['resume_anchor'] == 'await PR #9 CI'
        assert view.document['metadata'] == {'parallelization_scope': '2'}
        assert view.document['plans'] == [dict(row) for row in rows]
        assert 'updated' not in view.document

    def test_should_order_rows_by_seq_then_id(self, root):
        rows = (
            _row('PLAN-03', 'third', seq=2),
            _row('PLAN-02', 'second', seq=1),
            _row('PLAN-01', 'first', seq=2),
        )
        _ledger.write_layout(root, _header(), '', rows)

        view = _ledger.assemble_view(root)

        assert [row['id'] for row in view.document['plans']] == ['PLAN-02', 'PLAN-01', 'PLAN-03']

    def test_should_read_an_absent_queue_as_a_measured_empty_queue(self, root):
        _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert view.queue_state == _ledger.QUEUE_ABSENT
        assert view.document['plans'] == []
        assert view.document['resume_anchor'] == ''

    def test_should_report_an_unreadable_row_as_its_own_state(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1),))
        (_ledger.queue_dir(root) / 'PLAN-02.json').write_text('<<<<<<< HEAD\n{}\n', encoding='utf-8')
        (_ledger.queue_dir(root) / 'PLAN-03.json').write_text('[1]', encoding='utf-8')

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert [row['id'] for row in view.document['plans']] == ['PLAN-01']
        assert [row['file'] for row in view.unreadable_rows] == ['PLAN-02.json', 'PLAN-03.json']
        assert all(row['reason'] for row in view.unreadable_rows)

    def test_should_report_an_absent_header(self, root):
        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_ABSENT
        assert view.document == {}

    def test_should_report_an_unreadable_header_apart_from_an_absent_one(self, root):
        _ledger.header_path(root).write_text('not json', encoding='utf-8')

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_UNREADABLE
        assert view.document == {}

    def test_should_report_a_non_utf8_row_file_as_unreadable_without_raising(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1),))
        (_ledger.queue_dir(root) / 'PLAN-02.json').write_bytes(b'\xff\xfe')

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert [row['id'] for row in view.document['plans']] == ['PLAN-01']
        assert [row['file'] for row in view.unreadable_rows] == ['PLAN-02.json']
        assert 'not valid UTF-8' in view.unreadable_rows[0]['reason']

    def test_should_report_a_non_utf8_header_as_unreadable_without_raising(self, root):
        _ledger.header_path(root).write_bytes(b'\xff\xfe')

        probe = _ledger.probe_header(root)
        view = _ledger.assemble_view(root)

        assert probe.state == _ledger.LEDGER_UNREADABLE
        assert probe.observed_type == 'unreadable'
        assert 'not valid UTF-8' in probe.detail
        assert view.state == _ledger.LEDGER_UNREADABLE
        assert view.document == {}

    def test_should_report_a_non_utf8_anchor_as_unreadable_without_raising(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1),))
        _ledger.anchor_path(root).write_bytes(b'\xff\xfe')

        with pytest.raises(OSError, match='not valid UTF-8'):
            _ledger.read_anchor(root)
        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_UNREADABLE
        assert view.document == {}
        assert 'not valid UTF-8' in view.detail

    def test_should_ignore_non_row_files_in_the_queue(self, root):
        _ledger.write_layout(root, _header(), '', (_row('PLAN-01', 'first', seq=1),))
        (_ledger.queue_dir(root) / 'notes.txt').write_text('scratch', encoding='utf-8')

        view = _ledger.assemble_view(root)

        assert [row['id'] for row in view.document['plans']] == ['PLAN-01']
        assert view.unreadable_rows == ()
