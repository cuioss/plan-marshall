# SPDX-License-Identifier: FSL-1.1-ALv2
#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
from _manage_execution_manifest_subtraction_visibility_population_fixtures import (
    _derive_matrix_rule_keys,
    _drive_decision_matrix,
)

# =============================================================================
# The decision matrix — every reachable row reports its own narrowing
# =============================================================================


class TestDecisionMatrixRowsReportTheirNarrowing:
    """Half B, asserted over every reachable row with no per-row table at all.

    Five of these rows narrowed in complete silence before this plan. The
    assertions are applied to the WHOLE drive rather than to named rows, so a new
    matrix row is held to the same contract the moment it becomes reachable.
    """

    def test_the_drive_reaches_more_than_one_rule(self):
        """Guards the drive itself: a matrix that only ever returned the default
        row would make every assertion below vacuous."""
        assert len(_derive_matrix_rule_keys()) > 1

    def test_every_narrowing_row_emits_well_formed_records(self):
        for rule, removed, records in _drive_decision_matrix():
            if not removed:
                continue
            assert records, f"decide rule '{rule}' narrowed {removed} but reported nothing"
            assert all(set(r) == {'step', 'reason'} for r in records), (
                f"decide rule '{rule}' emitted a malformed record: {records}"
            )
            assert all(r['reason'] for r in records), f"decide rule '{rule}' emitted a record with no reason: {records}"

    def test_every_narrowing_row_names_exactly_the_steps_it_removed(self):
        for rule, removed, records in _drive_decision_matrix():
            assert {r['step'] for r in records} == set(removed), (
                f"decide rule '{rule}' reported {sorted({r['step'] for r in records})} "
                f'but removed {sorted(set(removed))}'
            )

    def test_a_row_that_narrows_nothing_reports_nothing(self):
        """The paired direction — no row may invent a subtraction it did not make."""
        for rule, removed, records in _drive_decision_matrix():
            if removed:
                continue
            assert records == [], f"decide rule '{rule}' reported {records} without narrowing"

    def test_at_least_one_row_narrows_and_one_does_not(self):
        """Both branches of the two tests above must actually be exercised."""
        rows = _drive_decision_matrix()

        assert any(removed for _rule, removed, _records in rows)
        assert any(not removed for _rule, removed, _records in rows)
