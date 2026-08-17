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

import re
from pathlib import Path

from _audit_fixtures import audit, minimal_corpus

#: The scalars a check may declare its EXAMINED population under — bound to the
#: production set rather than restated.
#:
#: A second hand-maintained copy is the very shape this guard exists to detect,
#: and it drifted once already: this list named `plans_with_merge_events` while
#: `_examined_population` did not read it, and no fixture reached the state where
#: the disagreement showed. `TestPopulationKeyCoverage` keeps the set honest from
#: the other side, asserting every `plans_*` scalar any emitter publishes is
#: classified as a denominator or as a documented non-denominator.
_EXAMINED_POPULATION_KEYS = audit._EXAMINED_POPULATION_KEYS

_EMPTY_POPULATION_RE = re.compile(
    rf"^(?:{'|'.join(_EXAMINED_POPULATION_KEYS)}):\s*0\s*$", re.MULTILINE
)


def _declares_empty_population(block: str) -> bool:
    """Does this block state, under ANY of its own names, that it examined nothing?

    Reads the block DIRECTLY rather than calling `audit._examined_population`, and
    that is the point. `_examined_population` applies precedence and falls back to
    the corpus size when it finds no declaration, so an expectation derived from it
    judges a block with an unread population key to have a FULL population — the
    same verdict the census reaches — and the contradiction (block says zero,
    census says "a non-empty examined population") is invisible to both sides. An
    earlier version of this helper did exactly that and passed against the broken
    code.

    The KEY SET is shared with production deliberately; the READING is not. Sharing
    the keys is what stops the two lists drifting apart, and reading independently
    is what stops the assertion becoming a restatement of the implementation.
    """
    return bool(_EMPTY_POPULATION_RE.search(block))


def _shipping_corpus(repo_root: Path) -> list:
    """A one-plan corpus whose plan SHIPS but carries no exploration counters.

    `minimal_corpus`'s plan records no `modified_files`, so it fails
    `_plan_shipped` and every delivery-cost check excludes it — which starves
    those checks by the shipping route and masks the `plans_in_corpus` axis. A
    non-empty `modified_files` makes the plan ship, so the shipping exclusion is
    zero and a check that still reports `plans_in_corpus: 0` did so by its OWN
    narrowing.
    """
    plan_dir = repo_root / ".plan" / "local" / "archived-plans" / "shipping-plan"
    plan_dir.mkdir(parents=True)
    (plan_dir / "references.json").write_text(
        '{"scope_estimate": "surgical", "modified_files": ["src/a.py"]}',
        encoding="utf-8",
    )
    (plan_dir / "status.json").write_text(
        '{"metadata": {"change_type": "bug_fix"}}', encoding="utf-8"
    )
    return [audit.collect_inputs(plan_dir)]

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


class TestNoCountAndExaminedPopulation:
    """The two ways a `disciplinary` verdict can be asserted without grounds."""

    def test_an_unread_count_is_no_count_not_disciplinary(self):
        """`None` means "no count was read" and must never render as a measured 0.

        `quality-chain` is such a block today: it emits
        `plan_genuine_signal_count` and `finding_genuine_signal_count` and no bare
        one, so `_GENUINE_COUNT_RE` records nothing for it. Defaulting that to 0
        and reporting `disciplinary` would have the census assert "a non-empty
        corpus was examined and nothing was genuine" on the strength of a default.
        """
        assert (
            audit._classify_zero(_MEASURED_ZERO_BLOCK, None, corpus_size=5)
            == audit._ZERO_NO_COUNT
        )

    def test_per_tier_genuine_counts_are_read_and_summed(self):
        """A multi-tier block states its total across per-tier lines, not one bare one.

        `quality-chain` publishes `plan_genuine_signal_count` and
        `finding_genuine_signal_count`. Reading only the bare spelling left it
        with no count on every run, so the census reported it a permanent suspect
        — including on runs where it FIRED, which is a constant rather than a
        detector.
        """
        block = (
            "check: quality-chain\nstatus: success\n"
            "plan_genuine_signal_count: 1\n"
            "finding_genuine_signal_count: 2\n"
        )
        assert audit._extract_per_check_genuine([block]) == {"quality-chain": 3}

    def test_a_bare_genuine_count_is_still_read(self):
        """The negative control — the widened read must not break the common shape."""
        assert audit._extract_per_check_genuine([_MEASURED_ZERO_BLOCK]) == {
            "dispatch-topology": 0
        }

    def test_a_firing_quality_chain_is_not_a_suspect(self, tmp_path: Path):
        """The consequence: a detector that produced positives is not suspect.

        D6's charter is to surface a detector that produced ZERO positives. One
        that fired must never appear in the suspect population, whatever spelling
        it used to state its count.
        """
        block = (
            "check: quality-chain\nstatus: success\n"
            "plan_genuine_signal_count: 1\n"
            "finding_genuine_signal_count: 1\n"
        )
        genuine = audit._extract_per_check_genuine([block])
        rows = audit.suspect_zero_census([block], genuine, {}, corpus_size=3)

        row = next(r for r in rows if r["check"] == "quality-chain")
        assert row["zero_class"] == audit._ZERO_NONE
        assert row["suspect"] == "false"

    def test_a_check_that_examined_no_plans_is_starved_not_disciplinary(self):
        """A delivery-cost check whose shipping partition excluded every plan.

        The corpus is non-empty, but this check saw nothing — so "a non-empty
        corpus was examined" is false of it. `_annotate_exclusions` stamps the
        count that makes the distinction available.
        """
        block = (
            "check: token-economics\nstatus: success\n"
            "plans_excluded_non_shipping: 5\n"
            "genuine_signal_count: 0\nrows[0]{a}:\n"
        )
        assert audit._classify_zero(block, 0, corpus_size=5) == audit._ZERO_STARVED

    def test_a_partially_excluded_check_is_still_disciplinary(self):
        """The discriminating half — exclusion alone does not mean starved."""
        block = (
            "check: token-economics\nstatus: success\n"
            "plans_excluded_non_shipping: 2\n"
            "genuine_signal_count: 0\nrows[3]{a}:\n"
        )
        assert audit._classify_zero(block, 0, corpus_size=5) == audit._ZERO_DISCIPLINARY

    def test_examined_population_defaults_to_the_whole_corpus(self):
        """A block with no exclusion line examined every plan."""
        assert audit._examined_population(_MEASURED_ZERO_BLOCK, 7) == 7

    def test_examined_population_never_goes_negative(self):
        block = "check: x\nplans_excluded_non_shipping: 9\n"
        assert audit._examined_population(block, 5) == 0


class TestPopulationKeyCoverage:
    """The key axis the whole-census guard does NOT quantify over.

    That guard loops over `CHECK_NAMES`, so a check cannot slip past it by being
    forgotten. But both it and `_examined_population` hard-code the KEY set, so a
    check can still slip past by publishing its population under a new name —
    which is the same enumeration shape, one axis over, and is exactly how
    `plans_in_series` and `plans_measured` went unread for five rounds.

    This narrows that axis: every key matching `f"plans_*:"` at the head of an
    f-string must be classified, either as a denominator `_examined_population`
    reads or as a deliberate non-denominator. A new key of that shape is a test
    failure rather than a silent gap.

    ⚠ It is a SHAPE-bounded guard, not a complete one. A population published
    under a different prefix, or assembled by concatenation rather than as an
    f-string literal, is invisible to the regex below and would slip through —
    verified by mutation. Today nothing does: every `plans_*` token in `audit.py`
    is classified. State the bound rather than claiming the axis is shut, because
    a guard believed stronger than it is is the defect this whole plan is about.
    """

    #: `plans_*` scalars that are NOT examined populations, each with its reason.
    #: Adding a key here is a claim; the docstring above says what the claim means.
    _NON_DENOMINATOR_KEYS = {
        # Zero means nothing was excluded — the population is FULL.
        "plans_excluded_non_shipping": "exclusion count",
        "plans_excluded_no_counters": "exclusion count",
        # `emit_table_block` emits `len(rows)` AFTER narrowing, so for the three
        # delivery-cost checks it routes (scope-estimate-accuracy,
        # task-count-efficiency, pr-merge-velocity) this IS the examined count,
        # not the corpus total. It is excluded anyway because those same blocks
        # carry the `plans_excluded_non_shipping` line `_examined_population`
        # reads at precedence 2, so the population is already established. A
        # FULL_CORPUS_CHECKS member that narrowed internally and emitted through
        # `emit_table_block` would be the gap — none does today.
        "plans_scanned": "narrowed row count; population established by the "
        "exclusion line these blocks also carry",
        # Numerators: how many plans landed in a result set. `plans_with_merge_events`
        # is the load-bearing case — `len(rows)`, how many plans HAD merge events.
        # Its check's substrate is the `[LOCK]` log, not the plan corpus, and an
        # absent log already reports `unmeasured`, so a readable log naming no merge
        # event is a genuine MEASURED zero and `disciplinary` is right for it.
        "plans_with_merge_events": "result count",
        "plans_without_ledger": "result count",
        "plans_without_ledger_ids": "result count",
    }

    def test_every_published_population_key_is_classified(self):
        published = set(
            re.findall(r'f"(plans_[a-z_]+):', _audit_source())
        )
        assert published, "no plans_* keys found — the sweep would pass vacuously"

        unclassified = published - set(_EXAMINED_POPULATION_KEYS) - set(
            self._NON_DENOMINATOR_KEYS
        )
        assert unclassified == set(), (
            f"unclassified population key(s): {sorted(unclassified)}. Either "
            "`_examined_population` must read it (and it joins "
            "`_EXAMINED_POPULATION_KEYS`), or it is not a denominator and joins "
            "`_NON_DENOMINATOR_KEYS` with its reason."
        )

    def test_every_denominator_key_is_read_by_the_production_reader(self):
        """A key this guard treats as a denominator the CODE must also read.

        The two lists disagreeing is what produced round 6's finding: the guard
        counted `plans_with_merge_events` as a population while
        `_examined_population` did not read it, and no fixture reached the state
        where that mattered.
        """
        for key in _EXAMINED_POPULATION_KEYS:
            block = f"check: x\nstatus: success\n{key}: 0\n"
            assert audit._examined_population(block, 7) == 0, key


def _audit_source() -> str:
    return Path(audit.__file__).read_text(encoding="utf-8")


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
