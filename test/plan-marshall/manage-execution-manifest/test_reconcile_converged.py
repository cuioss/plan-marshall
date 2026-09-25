# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_reconcile_fixtures import (
    REAL_A,
    REAL_B,
    _reconcile_ns,
    _seed_manifest,
    _write_marshal,
    cmd_reconcile,
)

# =============================================================================
# The no-divergence case
# =============================================================================


class TestConvergedManifestIsANoop:
    def test_converged_manifest_reports_no_changes(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A, REAL_B])
        _seed_manifest('rec-noop', [REAL_A, REAL_B], candidate_steps=[REAL_A, REAL_B])

        result = cmd_reconcile(_reconcile_ns('rec-noop', apply=True))
        assert result['status'] == 'success'
        assert result['stale'] == []
        assert result['broken'] == []
        assert result['backfill'] == []
        assert result['reconciled'] is False, 'a converged manifest is not a reconciliation'

    def test_missing_manifest_returns_file_not_found(self, plan_context):
        _write_marshal(plan_context.fixture_dir, [REAL_A])
        result = cmd_reconcile(_reconcile_ns('rec-absent'))
        assert result is None or result.get('error') == 'file_not_found'
