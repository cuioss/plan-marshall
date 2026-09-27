# SPDX-License-Identifier: FSL-1.1-ALv2

from _manage_status_orchestrator_ledger_fixtures import _ledger, json, root

# =============================================================================
# Header and anchor writes
# =============================================================================


class TestHeaderAndAnchorWrites:
    def test_should_create_a_header_without_queue_anchor_or_updated_keys(self, root):
        header = _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        on_disk = json.loads(_ledger.header_path(root).read_text(encoding='utf-8'))
        assert on_disk == header
        assert list(on_disk) == list(_ledger.HEADER_FIELDS)
        assert _ledger.anchor_path(root).read_text(encoding='utf-8') == '\n'

    def test_should_write_a_header_field_without_stamping_updated(self, root):
        _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        outcome = _ledger.write_header_field(root, 'phase', 'closed')

        assert outcome == {'previous': 'init'}
        on_disk = json.loads(_ledger.header_path(root).read_text(encoding='utf-8'))
        assert on_disk['phase'] == 'closed'
        assert 'updated' not in on_disk

    def test_should_set_a_metadata_entry(self, root):
        _ledger.create_ledger(root, 'Fresh', '2020-01-01T00:00:00Z')

        first = _ledger.set_metadata_field(root, 'owner', 'a')
        second = _ledger.set_metadata_field(root, 'owner', 'b')

        assert first == {'previous': None}
        assert second == {'previous': 'a'}
        assert json.loads(_ledger.header_path(root).read_text(encoding='utf-8'))['metadata'] == {'owner': 'b'}

    def test_should_report_legacy_from_inside_the_header_critical_section(self, root):
        legacy = {'kind': 'orchestrator', 'phase': 'init', 'plans': [], 'resume_anchor': ''}
        _ledger.header_path(root).write_text(json.dumps(legacy, indent=2), encoding='utf-8')

        assert _ledger.write_header_field(root, 'phase', 'closed') == {'legacy': True}
        assert _ledger.set_metadata_field(root, 'owner', 'x') == {'legacy': True}
        assert json.loads(_ledger.header_path(root).read_text(encoding='utf-8')) == legacy

    def test_should_round_trip_the_anchor_verbatim(self, root):
        _ledger.write_anchor(root, 'line one\nline two')

        text, _detail = _ledger.read_anchor(root)

        assert text == 'line one\nline two'

    def test_should_read_an_absent_anchor_as_empty(self, root):
        text, detail = _ledger.read_anchor(root)

        assert text == ''
        assert 'does not exist' in detail
