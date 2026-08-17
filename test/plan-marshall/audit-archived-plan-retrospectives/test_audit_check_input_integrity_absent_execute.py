#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``input-integrity`` — an ABSENT 5-execute phase is at least as blind as a zero.

``execute_blind`` drives the ``blind`` confidence bucket, the load-bearing case
that floors every downstream token figure for a plan. Its predecessor tested
``phase_tokens.get('5-execute', None) == 0``, which is ``False`` for an absent
phase — so the guard's precondition was the presence of the very record whose
absence it exists to detect. It was vacuous at exactly the value it was written to
catch, and green everywhere else.

The consequence was an INVERTED severity, which is what these tests pin: a plan
recording ``5-execute`` at zero tokens graded ``blind``, while a plan whose
metrics.toon has no ``5-execute`` section at all — strictly less recorded — graded
only ``partial``. Absence is never better-recorded than a recorded zero, so it can
never grade milder.
"""

from pathlib import Path

from _audit_fixtures import _write_ii_plan, audit


class TestAbsentExecutePhaseIsBlind:
    def test_absent_execute_phase_grades_blind(self, tmp_path: Path):
        inputs = _write_ii_plan(
            tmp_path, "absent-exec", phase_tokens={"4-plan": 500, "6-finalize": 200}
        )

        row = audit.check_input_integrity(inputs)

        assert "5-execute" not in row["metrics_blind"]
        assert row["incomplete_lifecycle"] == "5-execute"
        assert row["data_confidence"] == "blind"

    def test_zero_token_execute_still_grades_blind(self, tmp_path: Path):
        """The comparison case — unchanged behaviour, kept as the control."""
        inputs = _write_ii_plan(
            tmp_path,
            "zero-exec",
            phase_tokens={"4-plan": 500, "5-execute": 0, "6-finalize": 200},
        )

        row = audit.check_input_integrity(inputs)

        assert row["data_confidence"] == "blind"

    def test_absence_never_grades_milder_than_a_recorded_zero(self, tmp_path: Path):
        """The ordering property itself, stated as one assertion.

        Two plans differing ONLY in whether 5-execute is recorded-at-zero or
        missing entirely. The strictly-less-recorded one must not earn the
        strictly-better bucket.
        """
        recorded_zero = audit.check_input_integrity(
            _write_ii_plan(
                tmp_path,
                "ord-zero",
                phase_tokens={"4-plan": 500, "5-execute": 0, "6-finalize": 200},
            )
        )
        absent = audit.check_input_integrity(
            _write_ii_plan(
                tmp_path, "ord-absent", phase_tokens={"4-plan": 500, "6-finalize": 200}
            )
        )

        severity = {"fully-recorded": 0, "partial": 1, "blind": 2}
        assert (
            severity[absent["data_confidence"]]
            >= severity[recorded_zero["data_confidence"]]
        )

    def test_a_marker_explained_absent_execute_is_partial_not_blind(
        self, tmp_path: Path
    ):
        """A phase the recorder KNOWS was never closed is explained by design.

        The guard must widen to cover absence WITHOUT swallowing the
        marker-explained case — otherwise it would trade a false-clean verdict for
        a false-alarm one, and the #812 markers would stop meaning anything.
        """
        inputs = _write_ii_plan(
            tmp_path,
            "explained-absent",
            phase_tokens={"4-plan": 500, "6-finalize": 200},
            phases_missing_end_time="5-execute",
        )

        row = audit.check_input_integrity(inputs)

        assert row["data_confidence"] == "partial"

    def test_a_healthy_plan_is_unaffected(self, tmp_path: Path):
        """Non-vacuity: the widened guard does not mark every plan blind."""
        inputs = _write_ii_plan(tmp_path, "healthy-exec")

        row = audit.check_input_integrity(inputs)

        assert row["data_confidence"] == "fully-recorded"
