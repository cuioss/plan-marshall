# SPDX-License-Identifier: FSL-1.1-ALv2
"""Behavior-cluster tests carved from test_orchestrator_ledger.py: path."""

from _manage_status_orchestrator_ledger_fixtures import _ledger, pytest, root

# =============================================================================
# Path resolution
# =============================================================================


class TestPathResolution:
    def test_should_resolve_every_per_concern_path_under_the_root(self, root):
        assert _ledger.header_path(root) == root / 'status.json'
        assert _ledger.anchor_path(root) == root / 'resume_anchor.md'
        assert _ledger.queue_dir(root) == root / 'queue'
        assert _ledger.view_path(root) == root / 'queue-view.md'
        assert _ledger.row_path(root, 'PLAN-01') == root / 'queue' / 'PLAN-01.json'
        assert _ledger.row_path(root, 'PLAN-TRUTH-143') == root / 'queue' / 'PLAN-TRUTH-143.json'

    @pytest.mark.parametrize(
        'plan_id',
        ['../evil', 'PLAN-01/../x', 'PLAN-025B', 'PLAN-01\n', '', 'plan-01', 'PLAN-'],
    )
    def test_should_refuse_a_plan_id_outside_the_grammar(self, root, plan_id):
        assert _ledger.is_valid_row_id(plan_id) is False
        with pytest.raises(_ledger.LedgerPathError):
            _ledger.row_path(root, plan_id)

    def test_should_refuse_a_non_string_plan_id(self, root):
        assert _ledger.is_valid_row_id(None) is False
        assert _ledger.is_valid_row_id(7) is False
