#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``preference-pattern-detector`` aggregation — recurring (module, finding-class,
disposition) tuples are aggregated across the corpus and threshold-gated as
candidate preferences.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_preference_plan,
    audit,
)


class TestCrossPreferencePattern:
    """``cross_preference_pattern`` aggregates (module, finding-class, disposition)
    tuples across plans and surfaces any appearing in N>=threshold plans."""

    def test_tuple_in_three_plans_is_candidate(self, tmp_path: Path):
        # the same (module, finding-class, disposition) tuple in exactly 3 plans.
        all_inputs = [
            _write_preference_plan(
                tmp_path,
                f'plan-{i}',
                [{'title': 'Unused import: foo', 'resolution': 'suppressed', 'module': 'python'}],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        # colon suffix stripped, finding_class lowercased, count 3
        assert result['threshold'] == 3
        assert result['candidate_count'] == 1
        row = result['rows'][0]
        assert row['module'] == 'python'
        assert row['finding_class'] == 'unused import'
        assert row['disposition'] == 'suppressed'
        assert row['occurrence_count'] == 3
        assert row['plan_ids'] == ['plan-0', 'plan-1', 'plan-2']

    def test_tuple_below_threshold_not_surfaced(self, tmp_path: Path):
        # the tuple appears in only 2 plans — below the N>=3 threshold.
        all_inputs = [
            _write_preference_plan(
                tmp_path, p,
                [{'title': 'Magic number', 'resolution': 'accepted', 'module': 'python'}],
            )
            for p in ('plan-a', 'plan-b')
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0
        assert result['rows'] == []

    def test_non_user_gate_resolution_excluded(self, tmp_path: Path):
        # ``fixed`` and ``pending`` are NOT user-gate dispositions — excluded.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'plan-{i}',
                [{'title': 'Some finding', 'resolution': 'fixed', 'module': 'python'}],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0

    def test_promoted_finding_is_not_a_preference(self, tmp_path: Path):
        # a promoted (lesson) finding is never a preference even with a disposition.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'plan-{i}',
                [{'title': 'X', 'resolution': 'suppressed', 'module': 'python', 'promoted': True}],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0

    def test_distinct_dispositions_are_distinct_tuples(self, tmp_path: Path):
        # same module + finding-class, different disposition → two tuples, each
        # below threshold when split.
        all_inputs = []
        for i in range(2):
            all_inputs.append(
                _write_preference_plan(
                    tmp_path, f'sup-{i}',
                    [{'title': 'Dup code', 'resolution': 'suppressed', 'module': 'python'}],
                )
            )
        for i in range(2):
            all_inputs.append(
                _write_preference_plan(
                    tmp_path, f'acc-{i}',
                    [{'title': 'Dup code', 'resolution': 'accepted', 'module': 'python'}],
                )
            )

        result = audit.cross_preference_pattern(all_inputs)

        # neither disposition reaches 3 plans on its own
        assert result['candidate_count'] == 0

    def test_module_falls_back_to_component_then_default(self, tmp_path: Path):
        # no ``module``: falls back to ``component``, then ``default``.
        all_inputs = [
            _write_preference_plan(
                tmp_path, 'comp-0',
                [{'title': 'C', 'resolution': 'accepted', 'component': 'cli'}],
            ),
            _write_preference_plan(
                tmp_path, 'comp-1',
                [{'title': 'C', 'resolution': 'accepted', 'component': 'cli'}],
            ),
            _write_preference_plan(
                tmp_path, 'comp-2',
                [{'title': 'C', 'resolution': 'accepted', 'component': 'cli'}],
            ),
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 1
        assert result['rows'][0]['module'] == 'cli'

    def test_no_module_or_component_buckets_to_default(self, tmp_path: Path):
        # A finding with no module and no component still buckets to `default` —
        # but per D2 the `default` bucket is the UNATTRIBUTED sink and is NOT
        # promotable. The tuple is counted for visibility, never surfaced.
        all_inputs = [
            _write_preference_plan(
                tmp_path, f'd-{i}',
                [{'title': 'Cross', 'resolution': 'taken_into_account'}],
            )
            for i in range(3)
        ]

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0
        assert result['rows'] == []
        assert result['unattributed_excluded_count'] == 1

    def test_duplicate_tuple_within_plan_counts_once(self, tmp_path: Path):
        # one plan repeats the tuple; two others carry it once → 3 distinct plans.
        all_inputs = [
            _write_preference_plan(
                tmp_path, 'dup',
                [
                    {'title': 'Naming: a', 'resolution': 'suppressed', 'module': 'python'},
                    {'title': 'Naming: b', 'resolution': 'suppressed', 'module': 'python'},
                ],
            ),
            _write_preference_plan(
                tmp_path, 'p2',
                [{'title': 'Naming: c', 'resolution': 'suppressed', 'module': 'python'}],
            ),
            _write_preference_plan(
                tmp_path, 'p3',
                [{'title': 'Naming: d', 'resolution': 'suppressed', 'module': 'python'}],
            ),
        ]

        result = audit.cross_preference_pattern(all_inputs)

        row = result['rows'][0]
        assert row['occurrence_count'] == 3
        assert sorted(row['plan_ids']) == ['dup', 'p2', 'p3']

    def test_rows_sorted_by_descending_occurrence(self, tmp_path: Path):
        all_inputs = []
        for i in range(4):
            all_inputs.append(
                _write_preference_plan(
                    tmp_path, f'a-{i}',
                    [{'title': 'Alpha', 'resolution': 'suppressed', 'module': 'python'}],
                )
            )
        for i in range(3):
            all_inputs.append(
                _write_preference_plan(
                    tmp_path, f'b-{i}',
                    [{'title': 'Beta', 'resolution': 'accepted', 'module': 'python'}],
                )
            )

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 2
        assert result['rows'][0]['finding_class'] == 'alpha'
        assert result['rows'][0]['occurrence_count'] == 4
        assert result['rows'][1]['finding_class'] == 'beta'

    def test_no_findings_dir_yields_no_candidate(self, tmp_path: Path):
        all_inputs = []
        for i in range(3):
            plan_dir = tmp_path / '.plan' / 'temp' / 'pref-corpus' / f'bare-{i}'
            plan_dir.mkdir(parents=True, exist_ok=True)
            all_inputs.append(audit.collect_inputs(plan_dir))

        result = audit.cross_preference_pattern(all_inputs)

        assert result['candidate_count'] == 0
        assert result['rows'] == []
