#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``input-integrity`` presence detection and flagging — which corpus inputs are
detected as present or absent, and which absences raise a genuine signal.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_ii_plan,
    audit,
)


class TestInputIntegrityPresenceDetection:
    """``check_input_integrity`` reports a presence/health boolean (as a
    lowercase string) for every canonical input the plan dir carries."""

    def test_all_inputs_present_reports_true(self, tmp_path: Path):
        # a fully-populated plan dir
        inputs = _write_ii_plan(tmp_path, 'all-present')

        row = audit.check_input_integrity(inputs)

        # each presence flag is the string 'true'
        assert row['has_execution'] == 'true'
        assert row['has_metrics'] == 'true'
        assert row['has_references'] == 'true'
        assert row['has_tasks'] == 'true'
        assert row['has_findings'] == 'true'
        assert row['has_script_log'] == 'true'

    def test_missing_execution_manifest_reports_false(self, tmp_path: Path):
        # execution.toon omitted
        inputs = _write_ii_plan(tmp_path, 'no-exec', has_execution=False)

        row = audit.check_input_integrity(inputs)

        # only has_execution flips, the rest stay present
        assert row['has_execution'] == 'false'
        assert row['has_metrics'] == 'true'
        assert row['has_references'] == 'true'

    def test_missing_metrics_reports_false(self, tmp_path: Path):
        # work/metrics.toon omitted
        inputs = _write_ii_plan(tmp_path, 'no-metrics', has_metrics=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_metrics'] == 'false'

    def test_missing_references_reports_false(self, tmp_path: Path):
        # references.json omitted
        inputs = _write_ii_plan(tmp_path, 'no-refs', has_references=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_references'] == 'false'

    def test_empty_tasks_dir_reports_false(self, tmp_path: Path):
        # no TASK-*.json files
        inputs = _write_ii_plan(tmp_path, 'no-tasks', has_tasks=False)

        row = audit.check_input_integrity(inputs)

        # an absent (or empty) tasks dir reads as has_tasks=false
        assert row['has_tasks'] == 'false'

    def test_empty_findings_dir_reports_false(self, tmp_path: Path):
        # no *.jsonl findings files
        inputs = _write_ii_plan(tmp_path, 'no-findings', has_findings=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_findings'] == 'false'

    def test_missing_script_log_reports_false(self, tmp_path: Path):
        # no plan-scoped script-execution.log
        inputs = _write_ii_plan(tmp_path, 'no-log', has_script_log=False)

        row = audit.check_input_integrity(inputs)

        assert row['has_script_log'] == 'false'


class TestInputIntegrityFlags:
    """The three input-health flags — ``metrics_blind``, ``incomplete_lifecycle``,
    ``missing_dispatch_markers`` — each fire on their own primitive and clear on a
    fully-recorded plan."""

    def test_clean_plan_fires_no_flags(self, tmp_path: Path):
        # every input present, non-zero data-bearing phases, dispatch
        inputs = _write_ii_plan(tmp_path, 'clean')

        row = audit.check_input_integrity(inputs)

        # all three flag cells are empty
        assert row['metrics_blind'] == ''
        assert row['incomplete_lifecycle'] == ''
        assert row['missing_dispatch_markers'] == ''

    def test_zero_token_execute_sets_metrics_blind(self, tmp_path: Path):
        # a recorded 5-execute with zero tokens (the load-bearing case)
        inputs = _write_ii_plan(
            tmp_path, 'exec-blind',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
        )

        row = audit.check_input_integrity(inputs)

        # 5-execute is named in metrics_blind
        assert '5-execute' in row['metrics_blind']

    def test_zero_token_nonexecute_phase_sets_metrics_blind(self, tmp_path: Path):
        # a zero-token 6-finalize (data-bearing, but not the escalator)
        inputs = _write_ii_plan(
            tmp_path, 'finalize-blind',
            phase_tokens={'5-execute': 10_000, '6-finalize': 0},
        )

        row = audit.check_input_integrity(inputs)

        # 6-finalize is flagged blind; 5-execute (non-zero) is not
        assert '6-finalize' in row['metrics_blind']
        assert '5-execute' not in row['metrics_blind']

    def test_recorded_nonzero_phase_not_metrics_blind(self, tmp_path: Path):
        # both data-bearing phases carry tokens
        inputs = _write_ii_plan(
            tmp_path, 'no-blind',
            phase_tokens={'5-execute': 1, '6-finalize': 1},
        )

        row = audit.check_input_integrity(inputs)

        # no phase is blind
        assert row['metrics_blind'] == ''

    def test_missing_execute_phase_sets_incomplete_lifecycle(self, tmp_path: Path):
        # 5-execute section never recorded (only 6-finalize)
        inputs = _write_ii_plan(
            tmp_path, 'no-execute-phase',
            phase_tokens={'6-finalize': 5_000},
        )

        row = audit.check_input_integrity(inputs)

        # incomplete_lifecycle names the missing 5-execute
        assert '5-execute' in row['incomplete_lifecycle']

    def test_missing_finalize_phase_sets_incomplete_lifecycle(self, tmp_path: Path):
        # 6-finalize section never recorded (only 5-execute)
        inputs = _write_ii_plan(
            tmp_path, 'no-finalize-phase',
            phase_tokens={'5-execute': 10_000},
        )

        row = audit.check_input_integrity(inputs)

        # incomplete_lifecycle names the missing 6-finalize
        assert '6-finalize' in row['incomplete_lifecycle']

    def test_missing_dispatch_markers_flag_when_absent(self, tmp_path: Path):
        # work.log carries no [DISPATCH] role=phase-N line
        inputs = _write_ii_plan(tmp_path, 'no-dispatch', dispatch_marker=False)

        row = audit.check_input_integrity(inputs)

        # the marker-absence flag is the string 'true'
        assert row['missing_dispatch_markers'] == 'true'

    def test_dispatch_markers_present_clears_flag(self, tmp_path: Path):
        # work.log carries a [DISPATCH] role=phase-N marker
        inputs = _write_ii_plan(tmp_path, 'has-dispatch', dispatch_marker=True)

        row = audit.check_input_integrity(inputs)

        # the flag is empty
        assert row['missing_dispatch_markers'] == ''


class TestDataConfidenceBucket:
    """``data_confidence`` — BOTH routes into ``blind`` and the #812 carve-out.

    The shipped predicate is
    ``(execute_absent or execute_recorded_zero) and not execute_marker_explained``,
    and the docstring on ``check_input_integrity`` now states all three parts. This
    class is what keeps that statement honest: a docstring naming only the
    recorded-zero route reads as a complete specification of the bucket, and the
    predecessor's was wrong in BOTH directions — it excluded the absent route and
    omitted the carve-out.

    The ABSENT case is the load-bearing one. A reading built on
    ``phase_tokens.get('5-execute') == 0`` is False for an absent phase
    (``None == 0``), so it was vacuous at exactly the value it existed to catch,
    and it INVERTED the severity: a recorded zero graded ``blind`` while a strictly
    less-recorded absence graded only ``partial``.
    """

    def test_recorded_zero_execute_grades_blind(self, tmp_path: Path):
        # route 1: 5-execute present, stating zero tokens
        inputs = _write_ii_plan(
            tmp_path, 'dc-recorded-zero',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
        )

        assert audit.check_input_integrity(inputs)['data_confidence'] == 'blind'

    def test_absent_execute_grades_blind_not_partial(self, tmp_path: Path):
        # route 2: no 5-execute section at all. Absence is strictly LESS recorded
        # than a recorded zero, so it can never grade milder than the case above.
        inputs = _write_ii_plan(
            tmp_path, 'dc-absent',
            phase_tokens={'6-finalize': 5_000},
        )

        row = audit.check_input_integrity(inputs)

        assert row['data_confidence'] == 'blind'
        # named explicitly: `partial` here is the inverted-severity regression, and
        # a bare `!= fully-recorded` assertion would not have caught it.
        assert row['data_confidence'] != 'partial'

    def test_marker_explained_zero_execute_grades_partial_not_blind(self, tmp_path: Path):
        # the #812 carve-out: a zero-token 5-execute listed in
        # `phases_missing_end_time` was never CLOSED by design, so the gap is
        # explained rather than accidental.
        inputs = _write_ii_plan(
            tmp_path, 'dc-explained',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
            marker_schema='current',
            phases_missing_end_time='5-execute',
        )

        assert audit.check_input_integrity(inputs)['data_confidence'] == 'partial'

    def test_an_unreadable_marker_record_cannot_explain_a_zero(self, tmp_path: Path):
        """The presence read is THREE-state, and the third state explains nothing.

        `old-schema` and `pre-#812` are both "the record could not be read as a
        marker". Neither may buy a zero-token execute out of the blind set — an
        absence of explanation is not an explanation. This is the discriminating
        negative control for the carve-out above: were the carve-out keyed on
        anything weaker than an affirmative marker, these would grade `partial`.
        """
        for schema in ('old-schema', 'pre-#812'):
            inputs = _write_ii_plan(
                tmp_path, f'dc-unreadable-{schema.replace("#", "")}',
                phase_tokens={'5-execute': 0, '6-finalize': 5_000},
                marker_schema=schema,
                phases_missing_end_time='5-execute',
            )

            assert audit.check_input_integrity(inputs)['data_confidence'] == 'blind', schema

    def test_a_fully_recorded_plan_grades_fully_recorded(self, tmp_path: Path):
        # the positive control: without it, every assertion above would pass
        # against a predicate that graded literally every plan `blind`.
        inputs = _write_ii_plan(
            tmp_path, 'dc-clean',
            phase_tokens={'5-execute': 10_000, '6-finalize': 5_000},
        )

        assert audit.check_input_integrity(inputs)['data_confidence'] == 'fully-recorded'
