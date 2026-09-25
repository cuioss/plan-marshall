# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_status_orchestrator_ledger_fixtures import (
    _header,
    _ledger,
    json,
    pytest,
    root,
)

# =============================================================================
# The monolithic layout
# =============================================================================


class TestLegacyLayout:
    @pytest.mark.parametrize('key', ['plans', 'resume_anchor'])
    def test_should_detect_either_legacy_key(self, key):
        assert _ledger.detect_legacy({'kind': 'orchestrator', key: []}) is True

    def test_should_not_detect_a_per_concern_header(self):
        assert _ledger.detect_legacy(_header()) is False

    def test_should_refuse_to_assemble_a_legacy_ledger(self, root):
        _ledger.header_path(root).write_text(
            json.dumps({'kind': 'orchestrator', 'plans': [], 'resume_anchor': 'x'}), encoding='utf-8'
        )

        view = _ledger.assemble_view(root)

        assert view.state == _ledger.LEDGER_LEGACY
        assert view.document == {}

    def test_should_name_migrate_layout_as_the_remedy(self):
        error = _ledger.legacy_layout_error('my-epic')

        assert error['error'] == _ledger.LEGACY_LAYOUT_ERROR
        assert error['remedy'] == 'orchestrator migrate-layout --slug my-epic'
        assert error['remedy'] in error['message']
