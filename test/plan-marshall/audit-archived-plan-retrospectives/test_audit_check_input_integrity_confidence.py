#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""``input-integrity`` data confidence — the confidence tier a plan's inputs earn
and the genuine-signal predicate over it.
"""

from pathlib import Path

from _audit_fixtures import (
    _write_ii_plan,
    audit,
)


class TestInputIntegrityDataConfidence:
    """The per-plan ``data_confidence`` bucket: ``blind`` iff the 5-execute phase
    recorded zero tokens, else ``partial`` on any other gap/defect — including an
    UNREADABLE #812 marker record — else ``fully-recorded``."""

    def test_fully_recorded_when_no_gap_or_defect(self, tmp_path: Path):
        # every input present, every flag clear, marker record readable
        inputs = _write_ii_plan(tmp_path, 'fr')

        row = audit.check_input_integrity(inputs)

        assert row['data_confidence'] == 'fully-recorded'
        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_CURRENT

    def test_old_schema_marker_record_cannot_be_fully_recorded(self, tmp_path: Path):
        """An archived record still carrying `partial` / `unrecorded_phases`.

        Every input is present and every flag is clear — the ONLY difference from
        ``test_fully_recorded_when_no_gap_or_defect`` is the marker schema. The
        check could not establish that the plan is fully recorded, and "could not
        establish" must never render as `fully-recorded`.
        """
        inputs = _write_ii_plan(tmp_path, 'old-schema-ii', marker_schema='old-schema')

        row = audit.check_input_integrity(inputs)

        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_OLD
        assert row['data_confidence'] == 'partial'

    def test_pre_812_marker_record_is_distinguishable_from_old_schema(
        self, tmp_path: Path
    ):
        """A record carrying NEITHER pair reports `pre-#812`, not `old-schema`.

        Both bar `fully-recorded`, but they are different facts: an `old-schema`
        archive HAS markers a re-read could recover, a `pre-#812` one never had
        them. Collapsing the two is what the three-state read exists to prevent.
        """
        inputs = _write_ii_plan(tmp_path, 'pre812-ii', marker_schema='pre-#812')

        row = audit.check_input_integrity(inputs)

        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_PRE_812
        assert row['metrics_marker_schema'] != audit.METRICS_SCHEMA_OLD
        assert row['data_confidence'] == 'partial'

    def test_old_schema_zero_token_execute_is_blind_not_marker_explained(
        self, tmp_path: Path
    ):
        """An unreadable marker record explains NO zero-token phase.

        The pre-rename reader degraded an absent key to `(False, set())`, so
        after the rename every post-#812 archive would have read as "clean, and
        nothing to explain" — silently rescuing a genuinely blind execute out of
        the `blind` bucket. Here the retired keys DO name 5-execute, and the
        check still refuses to treat it as explained because it did not read them.
        """
        inputs = _write_ii_plan(
            tmp_path,
            'old-schema-blind',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
            marker_schema='old-schema',
            phases_missing_end_time='5-execute',
        )

        row = audit.check_input_integrity(inputs)

        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_OLD
        assert '5-execute' in row['metrics_blind']
        assert row['data_confidence'] == 'blind'

    def test_current_marker_explains_the_zero_token_execute(self, tmp_path: Path):
        """The positive control: a READABLE marker does rescue it into `partial`.

        Same fixture as the test above but with the CURRENT keys, so the refusal
        there is shown to come from the unreadable schema rather than from the
        check having stopped consulting markers at all.
        """
        inputs = _write_ii_plan(
            tmp_path,
            'current-marker-explained',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
            marker_schema='current',
            phases_missing_end_time='5-execute',
        )

        row = audit.check_input_integrity(inputs)

        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_CURRENT
        assert row['metrics_blind'] == ''
        assert row['data_confidence'] == 'partial'

    def test_zero_token_execute_is_blind(self, tmp_path: Path):
        # the load-bearing zero-token 5-execute
        inputs = _write_ii_plan(
            tmp_path, 'blind',
            phase_tokens={'5-execute': 0, '6-finalize': 5_000},
        )

        row = audit.check_input_integrity(inputs)

        # a blind 5-execute floors every downstream number
        assert row['data_confidence'] == 'blind'

    def test_missing_input_is_partial_not_blind(self, tmp_path: Path):
        # a missing input with a healthy (non-zero) 5-execute
        inputs = _write_ii_plan(tmp_path, 'partial-input', has_references=False)

        row = audit.check_input_integrity(inputs)

        # partial: a gap, but the load-bearing phase is not blind
        assert row['data_confidence'] == 'partial'

    def test_defect_without_blind_execute_is_partial(self, tmp_path: Path):
        # incomplete lifecycle (no 6-finalize) but 5-execute recorded
        inputs = _write_ii_plan(
            tmp_path, 'partial-defect',
            phase_tokens={'5-execute': 10_000},
        )

        row = audit.check_input_integrity(inputs)

        # partial, not blind: 5-execute carries tokens
        assert row['data_confidence'] == 'partial'

    def test_missing_optional_findings_alone_stays_fully_recorded(
        self, tmp_path: Path
    ):
        # only the OPTIONAL findings artefact absent, no flag fired
        inputs = _write_ii_plan(tmp_path, 'opt-findings', has_findings=False)

        row = audit.check_input_integrity(inputs)

        # findings is not part of the any_input_missing set, so the plan
        # remains fully-recorded
        assert row['data_confidence'] == 'fully-recorded'
        assert row['metrics_marker_schema'] == audit.METRICS_SCHEMA_CURRENT


class TestInputIntegrityGenuinePredicate:
    """``_input_integrity_genuine`` is the D1 severity predicate: genuine iff a
    real input-health defect fired (any of the three flags)."""

    def test_any_flag_is_genuine(self):
        # each flag alone makes the row genuine
        assert audit._input_integrity_genuine(
            {'metrics_blind': '5-execute',
             'incomplete_lifecycle': '',
             'missing_dispatch_markers': ''}
        ) is True
        assert audit._input_integrity_genuine(
            {'metrics_blind': '',
             'incomplete_lifecycle': '6-finalize',
             'missing_dispatch_markers': ''}
        ) is True
        assert audit._input_integrity_genuine(
            {'metrics_blind': '',
             'incomplete_lifecycle': '',
             'missing_dispatch_markers': 'true'}
        ) is True

    def test_no_flag_is_informational(self):
        # all flags empty => not genuine
        assert audit._input_integrity_genuine(
            {'metrics_blind': '',
             'incomplete_lifecycle': '',
             'missing_dispatch_markers': ''}
        ) is False
