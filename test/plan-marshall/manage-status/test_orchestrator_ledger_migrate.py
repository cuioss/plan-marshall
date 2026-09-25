# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_orchestrator_ledger_fixtures import _ledger, _row, root


class TestMigrateDocument:
    def _legacy(self) -> dict:
        return {
            'kind': 'orchestrator',
            'title': 'Legacy',
            'phase': 'orchestrating',
            'workstreams': ['WS-01', 'WS-02'],
            'plans': [
                _row('PLAN-03', 'third', status='shipped', pr='#12', landing='landings/PLAN-03.md'),
                _row('PLAN-01', 'first', status='running'),
                _row('PLAN-02', 'second'),
            ],
            'resume_anchor': 'await PR #12 CI',
            'metadata': {'parallelization_scope': '2'},
            'created': '2020-01-01T00:00:00Z',
            'updated': '2021-01-01T00:00:00Z',
        }

    def test_should_preserve_every_value_and_drop_updated(self):
        legacy = self._legacy()

        migrated = _ledger.migrate_document(legacy)

        assert migrated.header == {key: legacy[key] for key in _ledger.HEADER_FIELDS}
        assert 'updated' not in migrated.header
        assert migrated.anchor == 'await PR #12 CI'
        for original, converted in zip(legacy['plans'], migrated.rows, strict=True):
            assert {key: value for key, value in converted.items() if key != 'seq'} == original
        assert migrated.rejected_rows == ()

    def test_should_take_seq_from_array_order(self):
        migrated = _ledger.migrate_document(self._legacy())

        assert [(row['id'], row['seq']) for row in migrated.rows] == [('PLAN-03', 1), ('PLAN-01', 2), ('PLAN-02', 3)]

    def test_should_reproduce_the_legacy_order_after_materialising(self, root):
        legacy = self._legacy()
        migrated = _ledger.migrate_document(legacy)

        _ledger.write_layout(root, migrated.header, migrated.anchor, migrated.rows)
        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_OK
        assert [row['id'] for row in view.document['plans']] == ['PLAN-03', 'PLAN-01', 'PLAN-02']
        assert view.document['resume_anchor'] == legacy['resume_anchor']
        assert view.document['workstreams'] == legacy['workstreams']

    def test_should_report_rows_it_cannot_convert_instead_of_dropping_them(self):
        legacy = self._legacy()
        legacy['plans'].append('not-a-row')
        legacy['plans'].append(_row('PLAN-025B', 'lettered'))

        migrated = _ledger.migrate_document(legacy)

        assert len(migrated.rows) == 3
        assert [(row['index'], row['id']) for row in migrated.rejected_rows] == [('3', ''), ('4', 'PLAN-025B')]
        assert all(row['reason'] for row in migrated.rejected_rows)
