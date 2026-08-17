#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The suspect-zero census — the class guard.

A detector that has never produced a positive is indistinguishable, from its
output alone, from one that CANNOT produce one. The census makes every zero
SUSPECT rather than silently clean, and classifies what KIND of zero it is:

* ``structural`` — the check declared it could not measure. Not evidence.
* ``starved`` — the corpus supplied no plans. Not evidence either, for a
  different reason, and with a different remedy.
* ``disciplinary`` — a non-empty corpus was examined and nothing was genuine.
  Evidence about the corpus; never proof the check is able to fire.

The distinction is the deliverable. A census that lumped the three together
would report the same thing for a check whose predicate cannot fire and a check
that is doing its job over a clean corpus.
"""

from pathlib import Path

from _audit_fixtures import audit, minimal_corpus

_UNMEASURED_BLOCK = (
    "check: merge-window-accounting\nstatus: unmeasured\nunmeasured_reason: no substrate\n"
)
_MEASURED_ZERO_BLOCK = (
    "check: dispatch-topology\nstatus: success\ngenuine_signal_count: 0\nrows[3]{a}:\n"
)
_FIRED_BLOCK = (
    "check: dispatch-topology\nstatus: success\ngenuine_signal_count: 2\nrows[3]{a}:\n"
)


class TestZeroClassification:
    def test_unmeasured_status_is_a_structural_zero(self):
        assert (
            audit._classify_zero(_UNMEASURED_BLOCK, 0, corpus_size=5)
            == audit._ZERO_STRUCTURAL
        )

    def test_empty_corpus_is_a_starved_zero(self):
        assert (
            audit._classify_zero(_MEASURED_ZERO_BLOCK, 0, corpus_size=0)
            == audit._ZERO_STARVED
        )

    def test_measured_zero_over_a_real_corpus_is_disciplinary(self):
        assert (
            audit._classify_zero(_MEASURED_ZERO_BLOCK, 0, corpus_size=5)
            == audit._ZERO_DISCIPLINARY
        )

    def test_a_check_that_fired_is_not_a_suspect(self):
        assert audit._classify_zero(_FIRED_BLOCK, 2, corpus_size=5) == audit._ZERO_NONE

    def test_structural_outranks_starved(self):
        """An unmeasured check is structural even on an empty corpus.

        The check's own declaration is stronger evidence than the corpus size:
        it would not have measured whatever the corpus held.
        """
        assert (
            audit._classify_zero(_UNMEASURED_BLOCK, 0, corpus_size=0)
            == audit._ZERO_STRUCTURAL
        )


class TestCensusRows:
    def test_every_registered_check_gets_a_row(self):
        rows = audit.suspect_zero_census([], {}, {}, corpus_size=3)
        assert [r["check"] for r in rows] == list(audit.CHECK_NAMES)

    def test_a_check_that_emitted_no_block_is_itself_reported(self):
        """A detector that silently stopped emitting is the completest failure."""
        rows = audit.suspect_zero_census([], {}, {}, corpus_size=3)
        assert all(r["zero_class"] == "no_block" for r in rows)
        assert all(r["suspect"] == "true" for r in rows)

    def test_a_deliberately_starved_detector_is_surfaced_as_suspect(self):
        """The plan's acceptance: starve a detector, and the census must say so.

        `merge-window-accounting` has no `[LOCK]` substrate here, so it reports
        `unmeasured` and its zero is classified `structural` — not silently clean,
        and not conflated with a check that looked and found nothing.
        """
        rows = audit.suspect_zero_census(
            [_UNMEASURED_BLOCK, _MEASURED_ZERO_BLOCK],
            {"merge-window-accounting": 0, "dispatch-topology": 0},
            {},
            corpus_size=5,
        )
        by_check = {r["check"]: r for r in rows}

        starved = by_check["merge-window-accounting"]
        assert starved["suspect"] == "true"
        assert starved["zero_class"] == audit._ZERO_STRUCTURAL
        assert "NOT evidence" in starved["reading"]

        # The discriminating half: a check over the SAME corpus that did measure
        # is classified differently. Without this the test would pass on a census
        # that called everything structural.
        clean = by_check["dispatch-topology"]
        assert clean["zero_class"] == audit._ZERO_DISCIPLINARY
        assert clean["suspect"] == "true"

    def test_quiet_streak_is_carried_per_check(self):
        rows = audit.suspect_zero_census(
            [_MEASURED_ZERO_BLOCK], {"dispatch-topology": 0}, {"dispatch-topology": 7}, 5
        )
        row = next(r for r in rows if r["check"] == "dispatch-topology")
        assert row["quiet_run_count"] == 7


class TestQuietStreaks:
    def test_streak_counts_consecutive_recorded_zeros(self):
        runs = [{"metrics": 0}, {"metrics": 0}, {"metrics": 3}]
        assert audit.quiet_streaks(runs)["metrics"] == 2

    def test_a_missing_record_breaks_the_streak(self):
        """An absent record is not a recorded zero.

        A check that stopped emitting must not accrue quiet runs toward its own
        retirement — which is also how an `unmeasured` run is kept out of the
        streak, since it publishes no genuine count.
        """
        runs = [{"metrics": 0}, {}, {"metrics": 0}]
        assert audit.quiet_streaks(runs)["metrics"] == 1

    def test_a_nonzero_first_run_yields_no_streak(self):
        assert audit.quiet_streaks([{"metrics": 1}, {"metrics": 0}])["metrics"] == 0


class TestCensusBlock:
    def test_block_carries_class_counts_and_the_reading_note(self):
        rows = audit.suspect_zero_census(
            [_UNMEASURED_BLOCK, _FIRED_BLOCK],
            {"merge-window-accounting": 0, "dispatch-topology": 2},
            {},
            corpus_size=5,
        )
        block = audit.emit_suspect_zero_census_block(rows, corpus_size=5)

        assert "check: suspect-zero-census" in block
        assert "structural_count: 1" in block
        assert "census_note:" in block
        assert "a zero is not a clean verdict" in block
        assert f"checks_registered: {len(audit.CHECK_NAMES)}" in block

    def test_full_sweep_emits_the_census(self, tmp_path: Path):
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        assert "check: suspect-zero-census" in output
        # It reports; it never proposes or blocks. The retirement reading lives in
        # its own block and the two are emitted together, so a quiet check is
        # never presented with only one of the two readings available.
        assert "check: retire-on-quiet" in output

    def test_census_and_retire_on_quiet_agree_on_the_streak(self, tmp_path: Path):
        """Both blocks read one derivation, so they cannot disagree about it."""
        runs = [{"metrics": 0}, {"metrics": 0}]
        streaks = audit.quiet_streaks(runs)
        rows = audit.suspect_zero_census(
            [_MEASURED_ZERO_BLOCK.replace("dispatch-topology", "metrics")],
            {"metrics": 0},
            streaks,
            corpus_size=4,
        )
        row = next(r for r in rows if r["check"] == "metrics")
        assert row["quiet_run_count"] == streaks["metrics"] == 2
