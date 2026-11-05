# SPDX-License-Identifier: FSL-1.1-ALv2
"""The boundary reader keeps a prescribed build hand-back its own population.

The four cases the hand-back cause has to survive at the reader edge:

* a file whose ONLY rows carry the new cause;
* a file that MIXES the new cause with ``voluntary_checkpoint``;
* a file that carries NEITHER;
* two consecutive hand-back rows for the same task (a re-attach).

The count is per cause and per row: a run of hand-back rows never collapses into
one, never takes on the neighbouring ``voluntary_checkpoint`` cause, and never
enters the voluntary-checkpoint polling detector — which reads the WORK log, not
this artifact, so a hand-back row cannot register as polling in the first place.
"""

from __future__ import annotations

from _analyze_logs_fixtures import _analyze_logs

_HEADER = 'rows[]{timestamp,termination_cause,total_tokens,tool_uses,duration_ms}:\n'


def _write(plan_dir, rows: list[str]) -> None:
    (plan_dir / 'work').mkdir(parents=True, exist_ok=True)
    (plan_dir / 'work' / 'metrics-dispatch-boundaries-5-execute.toon').write_text(
        'plan_id: boundary-fixture\nphase: 5-execute\n' + _HEADER + ''.join(rows),
        encoding='utf-8',
    )


def _parse(plan_dir):
    return _analyze_logs.read_dispatch_boundaries_per_phase(plan_dir)['5-execute']


class TestHandbackRowsAreTheirOwnPopulation:
    def test_a_file_of_only_handback_rows_counts_them_and_nothing_else(self, tmp_path):
        _write(
            tmp_path,
            [
                '2026-05-08T14:00:00Z,verification_handback,100,2,1000\n',
                '2026-05-08T14:01:00Z,verification_handback,200,4,2000\n',
            ],
        )

        parsed = _parse(tmp_path)

        assert parsed['present'] is True
        assert parsed['verification_handback_count'] == 2
        assert parsed['clean_exit_queue_empty_count'] == 0
        assert parsed['returned_with_findings_count'] == 0
        # The rows keep their own cause — no neighbour is invented.
        assert [row['termination_cause'] for row in parsed['rows']] == [
            'verification_handback',
            'verification_handback',
        ]
        # A hand-back is a productive prescribed yield, never terminal waste.
        assert parsed['error_total_tokens'] == 0
        assert parsed['retryable_total_tokens'] == 0

    def test_a_mixed_file_counts_the_handbacks_beside_the_voluntary_rows(self, tmp_path):
        _write(
            tmp_path,
            [
                '2026-05-08T14:00:00Z,voluntary_checkpoint,100,2,1000\n',
                '2026-05-08T14:01:00Z,verification_handback,200,4,2000\n',
                '2026-05-08T14:02:00Z,voluntary_checkpoint,300,6,3000\n',
            ],
        )

        parsed = _parse(tmp_path)

        assert parsed['verification_handback_count'] == 1
        voluntary = [row for row in parsed['rows'] if row['termination_cause'] == 'voluntary_checkpoint']
        assert len(voluntary) == 2
        # The mixed fixture's voluntary rows are counted exactly as they are in a
        # file that carries only voluntary rows — the hand-back neither adds to
        # nor subtracts from that population.
        assert sum(row['total_tokens'] for row in voluntary) == 400

    def test_a_file_with_neither_cause_reports_zero_handbacks(self, tmp_path):
        _write(tmp_path, ['2026-05-08T14:00:00Z,clean_exit_queue_empty,100,2,1000\n'])

        parsed = _parse(tmp_path)

        assert parsed['verification_handback_count'] == 0
        assert parsed['clean_exit_queue_empty_count'] == 1

    def test_two_consecutive_handback_rows_for_one_task_are_both_kept(self, tmp_path):
        """A re-attach writes two rows for the same step; neither is collapsed."""
        _write(
            tmp_path,
            [
                '2026-05-08T14:00:00Z,verification_handback,100,2,1000,unmeasured,unmeasured,unmeasured,unmeasured,verify:module-tests\n',
                '2026-05-08T14:01:00Z,verification_handback,150,3,1500,unmeasured,unmeasured,unmeasured,unmeasured,verify:module-tests\n',
            ],
        )

        parsed = _parse(tmp_path)

        assert parsed['verification_handback_count'] == 2
        assert len(parsed['rows']) == 2
        # An absent artifact reports the SAME key at zero — a reader never has to
        # test for presence before reading the count.
        absent = tmp_path / 'no-boundary'
        absent.mkdir()
        assert _analyze_logs.read_dispatch_boundaries_per_phase(absent) == {}


class TestHandbackRowsAreNotPollingEvidence:
    def test_a_work_log_of_handback_evidence_never_meets_the_polling_precondition(self):
        """The polling detector reads the WORK log, so boundary rows cannot feed it.

        A hand-back leaves no ``[ATTEMPT]`` line — the leaf returned instead of
        dispatching — so the precondition is unmet and the pair count is zero by
        construction, not by a special case.
        """
        work_lines = [
            '2026-05-08T14:00:00Z [INFO] (plan-marshall:phase-5-execute) Verification handed back: verify:module-tests',
            '2026-05-08T14:00:01Z [INFO] (plan-marshall:phase-5-execute) Returning control to orchestrator',
        ]

        result = _analyze_logs.detect_voluntary_checkpoint_polling(work_lines)

        assert result['precondition_met'] is False
        assert result['polling_pairs_count'] == 0
