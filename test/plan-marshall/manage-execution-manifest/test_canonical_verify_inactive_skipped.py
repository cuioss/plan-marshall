# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_canonical_verify_inactive_fixtures import _entry_for, _execution_row, _summarize_refires


class TestSkippedRowsNeverFire:
    """A skipped/inactive canonical contributes no firing — green is unreachable without a verdict.

    Pins the ``summarize_refires`` half of the fail-closed green-report
    binding: only an ``executed`` row is a firing, so a canonical that never
    ran (every row ``skipped``, or no row at all) leaves ``firings == 0`` and
    no downstream report may read green off it.
    """

    def test_skipped_only_step_has_zero_firings(self):
        steps, _totals = _summarize_refires(
            [
                _execution_row('verify:integration-tests', 'skipped'),
                _execution_row('verify:integration-tests', 'skipped'),
            ]
        )
        entry = _entry_for(steps, 'verify:integration-tests')
        assert entry['firings'] == 0
        assert entry['refires'] == 0
        assert entry['skipped'] == 2

    def test_skipped_rows_do_not_fold_into_firings(self):
        steps, _totals = _summarize_refires(
            [
                _execution_row('verify:quality-gate', 'executed'),
                _execution_row('verify:quality-gate', 'skipped'),
                _execution_row('verify:quality-gate', 'skipped'),
            ]
        )
        entry = _entry_for(steps, 'verify:quality-gate')
        assert entry['firings'] == 1
        assert entry['refires'] == 0
        assert entry['skipped'] == 2

    def test_single_executed_row_is_one_firing_with_no_refire(self):
        steps, _totals = _summarize_refires([_execution_row('verify:module-tests', 'executed')])
        entry = _entry_for(steps, 'verify:module-tests')
        assert entry['firings'] == 1
        assert entry['refires'] == 0
