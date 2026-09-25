# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_canonical_verify_inactive_fixtures import _entry_for, _execution_row, _summarize_refires


class TestRefireCountingBoundsTriageIterations:
    """The refire arithmetic the triage-iteration bound consumes.

    ``refires`` is ``max(0, firings - 1)`` per step — the first ``executed``
    row is the firing the pipeline owes, every later one is an extra firing.
    Non-completion outcomes (``failed`` / ``error`` / ``loop_back``) are
    counted apart and never inflate the firing count, so a thorough gate that
    needed several triage rounds is measured, not misgraded.
    """

    def test_three_executions_yield_two_refires(self):
        steps, totals = _summarize_refires([_execution_row('verify:quality-gate', 'executed')] * 3)
        entry = _entry_for(steps, 'verify:quality-gate')
        assert entry['firings'] == 3
        assert entry['refires'] == 2
        assert totals['refires'] == 2

    def test_failures_and_errors_do_not_inflate_firings(self):
        steps, _totals = _summarize_refires(
            [
                _execution_row('verify:module-tests', 'executed'),
                _execution_row('verify:module-tests', 'failed'),
                _execution_row('verify:module-tests', 'error'),
                _execution_row('verify:module-tests', 'executed'),
            ]
        )
        entry = _entry_for(steps, 'verify:module-tests')
        assert entry['firings'] == 2
        assert entry['refires'] == 1
        assert entry['failures'] == 1
        assert entry['errors'] == 1
