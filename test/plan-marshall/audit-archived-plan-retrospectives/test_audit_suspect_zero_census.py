#!/usr/bin/env python3
# SPDX-License-Identifier: FSL-1.1-ALv2
"""The suspect-zero census — the class guard."""


from pathlib import Path

from _audit_fixtures import audit, minimal_corpus
from _audit_suspect_zero_census_fixtures import (
    _FIRED_BLOCK,
    _MEASURED_ZERO_BLOCK,
    _UNMEASURED_BLOCK,
    _declares_empty_population,
    _shipping_corpus,
)


def _gated_block(*, excluded: int, examined: int = 4, genuine: int = 0) -> str:
    """A `preference-pattern-detector` block whose declared gate excluded rows.

    `excluded` is the block's own `unattributed_excluded_count` — how many
    qualifying recurrences its unattributed-bucket gate declined to surface. It
    is a parameter rather than a fixed literal because the discriminating case is
    the pair: a non-zero count is the gate speaking, and a zero one leaves the
    verdict where it was.
    """
    return (
        "check: preference-pattern-detector\nstatus: success\n"
        f"plans_in_corpus: {examined}\n"
        f"unattributed_excluded_count: {excluded}\n"
        f"genuine_signal_count: {genuine}\nrows[0]{{a}}:\n"
    )


class TestGatedZero:
    """A zero produced by the check's OWN declared gate, not by a clean corpus.

    `disciplinary` asserts "a non-empty examined population and nothing genuine"
    — evidence about the corpus. When the block's own exclusion count records
    that a declared gate declined every qualifying row, the corpus was not clean:
    the gate emptied the result, so the zero is evidence about the gate and the
    remedy is to its calibration rather than to the inputs.
    """

    def test_a_gate_that_declined_every_row_is_gated_not_disciplinary(self):
        assert (
            audit._classify_zero(_gated_block(excluded=2), 0, corpus_size=4)
            == audit._ZERO_GATED
        )

    def test_a_gate_that_declined_nothing_is_still_disciplinary(self):
        """The discriminating half — without it the test above would pass on a
        classifier that called every preference block `gated`."""
        assert (
            audit._classify_zero(_gated_block(excluded=0), 0, corpus_size=4)
            == audit._ZERO_DISCIPLINARY
        )

    def test_a_block_that_fired_is_not_gated(self):
        """A gate that declined some rows while others still surfaced is not a
        suspect at all — `fired` outranks every zero class."""
        assert (
            audit._classify_zero(_gated_block(excluded=2, genuine=3), 3, corpus_size=4)
            == audit._ZERO_NONE
        )

    def test_starved_outranks_gated(self):
        """A check that examined NO plans is starved whatever its gate did.

        There was no qualifying row for the gate to decline, so attributing the
        zero to the gate would name the wrong cause — and the remedies differ.
        """
        assert (
            audit._classify_zero(_gated_block(excluded=2, examined=0), 0, corpus_size=0)
            == audit._ZERO_STARVED
        )

    def test_structural_outranks_gated(self):
        """An `unmeasured` block's own declaration outranks its exclusion count."""
        block = _UNMEASURED_BLOCK + "unattributed_excluded_count: 2\n"
        assert audit._classify_zero(block, 0, corpus_size=5) == audit._ZERO_STRUCTURAL


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

    def test_structural_outranks_no_count(self):
        """An unmeasured block withholds its count BY DESIGN.

        The withholding is how an unmeasured check stays out of the
        retire-on-quiet streak, so the absent count is a consequence of the
        declaration rather than an independent fact. Reporting `no_count` here
        would surface the symptom and discard the reason the block already gave —
        and `merge-window-accounting` is exactly this shape on a real sweep.
        """
        assert (
            audit._classify_zero(_UNMEASURED_BLOCK, None, corpus_size=5)
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


class TestCensusEndToEnd:
    """Joins the real emitter to the real classification.

    Building the block by hand and asserting on it is the shape the plan calls
    out for D3 — a suite that synthesises its own marker cannot see the emitter
    drift away from it. These assertions run a real sweep.
    """

    def test_a_starved_detector_is_structural_on_a_real_sweep(self, tmp_path: Path):
        """`merge-window-accounting` has no `[LOCK]` substrate in this corpus."""
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        row = next(
            ln
            for ln in output.splitlines()
            if ln.strip().startswith("merge-window-accounting,")
        )
        assert audit._ZERO_STRUCTURAL in row
        assert ",true," in row

    def test_a_measuring_check_over_the_same_sweep_is_classified_differently(
        self, tmp_path: Path
    ):
        """The discriminator — without it this would pass on an all-structural census."""
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        row = next(
            ln
            for ln in output.splitlines()
            if ln.strip().startswith("dispatch-topology,")
        )
        assert audit._ZERO_STRUCTURAL not in row

    def test_no_registered_check_reports_disciplinary_over_an_empty_population(
        self, tmp_path: Path
    ):
        """No check may claim a population its own block says it did not have.

        A `disciplinary` row asserts "a non-empty examined population and nothing
        genuine". That is legitimate for a check that examined the whole corpus
        and found nothing, and FALSE for one whose own block declares an empty
        population — the block and the census then contradict each other one line
        apart.

        ⭐ The loop is over `CHECK_NAMES`, deliberately, and that is the whole
        value of this test. Five verification rounds each found this same defect
        in a check the previous round had not looked at, because every fix was
        scoped to the sites someone had thought to enumerate: first one check,
        then its two siblings sharing a predicate, then two more that narrowed on
        different axes entirely. A hard-coded name list reproduces that failure by
        construction. Quantifying over the registry means a check added later —
        or one that starts narrowing later — is covered without anyone
        remembering to add it here.
        """
        inputs = _shipping_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)
        blocks = {
            name: output.split(f"check: {name}\n", 1)[1].split("\ncheck: ", 1)[0]
            for name in audit.CHECK_NAMES
        }
        census = output.split("check: suspect-zero-census", 1)[1]

        offenders = []
        for check in audit.CHECK_NAMES:
            row = next(
                ln for ln in census.splitlines() if ln.strip().startswith(f"{check},")
            )
            if f",{audit._ZERO_DISCIPLINARY}," not in row:
                continue
            if _declares_empty_population(blocks[check]):
                offenders.append(check)

        assert offenders == []

    def test_a_readable_lock_log_with_no_merge_events_is_a_measured_zero(
        self, tmp_path: Path
    ):
        """The census fixture that reaches merge-window-accounting's measured path.

        No census fixture staged a lock log, so this check only ever reached the
        census via its `unmeasured` branch — and a disagreement between this
        guard's key list and `_examined_population` about `plans_with_merge_events`
        sat unseen because nothing exercised the state where they differ.

        The state is ordinary: `log_lock_event` writes BOTH lock families to the
        same dated file, so any repo with build-queue activity and no concurrent
        merges lands here. It is a MEASURED zero — the substrate was read and the
        corpus genuinely had no merge contention — so `disciplinary` is correct and
        `starved` would be wrong.
        """
        logs_dir = tmp_path / ".plan" / "logs"
        logs_dir.mkdir(parents=True)
        (logs_dir / "lock-2026-07-01.log").write_text(
            "[2026-07-01T10:00:00Z] [INFO] [a] [LOCK] (build:acquired) some-plan\n",
            encoding="utf-8",
        )
        inputs = _shipping_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        block = output.split("check: merge-window-accounting\n", 1)[1].split(
            "\ncheck: ", 1
        )[0]
        assert "status: success" in block
        assert "plans_with_merge_events: 0" in block
        assert not _declares_empty_population(block)

        census = output.split("check: suspect-zero-census", 1)[1]
        row = next(
            ln
            for ln in census.splitlines()
            if ln.strip().startswith("merge-window-accounting,")
        )
        assert f",{audit._ZERO_DISCIPLINARY}," in row

    def test_no_registered_check_is_classified_no_count_on_a_real_sweep(
        self, tmp_path: Path
    ):
        """Every emitted block states a genuine total the census can read.

        `no_count` is a defensive class for a block that publishes none. A check
        landing there on a normal sweep means the census is reporting a permanent
        suspect about a detector it simply cannot read — which is a constant, not
        a detector, and `quality-chain` was exactly that until its per-tier counts
        were made readable.
        """
        inputs = minimal_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        census = output.split("check: suspect-zero-census", 1)[1]
        offenders = [
            ln.strip()
            for ln in census.splitlines()
            if f",{audit._ZERO_NO_COUNT}," in ln
        ]
        assert offenders == []

    def test_a_check_narrowing_its_own_population_to_zero_is_starved(
        self, tmp_path: Path
    ):
        """A SHIPPING plan that a check narrows out on its own axis.

        The corpus must ship, and this is the whole point of the fixture. On a
        non-shipping corpus `exploration-share` is starved via the
        shipping-exclusion route, so the row reads `starved` whether or not
        `plans_in_corpus` is read at all — an assertion that cannot fail is not a
        guard. A shipping plan with no exploration counters isolates the
        `plans_in_corpus` axis: the shipping exclusion is zero, and only the
        check's own declared population makes it starved.

        The verdict is asserted POSITIVELY. A negative-only assertion
        (`disciplinary not in row`) also passes on a regression to `no_count` or
        `fired`, which is no verdict at all.
        """
        inputs = _shipping_corpus(tmp_path)
        output = audit.run_checks(inputs, list(audit.CHECK_NAMES), tmp_path)

        census = output.split("check: suspect-zero-census", 1)[1]
        row = next(
            ln for ln in census.splitlines() if ln.strip().startswith("exploration-share,")
        )
        assert f",{audit._ZERO_STARVED}," in row

    def test_the_shipping_fixture_really_ships(self, tmp_path: Path):
        """Non-vacuity control for the test above.

        If the plan stopped shipping, the assertion would pass via the exclusion
        route and stop testing `plans_in_corpus` — silently. This pins the
        precondition that makes the test above discriminating.
        """
        inputs = _shipping_corpus(tmp_path)
        shipping, excluded = audit._partition_shipping(inputs)

        assert [i.plan_id for i in shipping] == ["shipping-plan"]
        assert excluded == []


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

    def test_block_tallies_the_gated_class(self):
        """A gated zero is counted on its own axis, not folded into disciplinary.

        Classifying it correctly and then tallying it under `disciplinary_count`
        would republish, one line up, the very reading the class exists to
        withhold — so both counts are asserted as a pair.
        """
        rows = audit.suspect_zero_census(
            [_gated_block(excluded=2), _MEASURED_ZERO_BLOCK],
            {"preference-pattern-detector": 0, "dispatch-topology": 0},
            {},
            corpus_size=4,
        )
        block = audit.emit_suspect_zero_census_block(rows, corpus_size=4)

        assert "gated_count: 1" in block
        assert "disciplinary_count: 1" in block   # the sibling stayed where it was

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
