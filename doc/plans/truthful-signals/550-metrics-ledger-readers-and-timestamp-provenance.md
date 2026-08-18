> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Metrics, ledger readers and rendered-timestamp provenance stop reading an absence as a measurement

**Epic:** truthful-signals
**Branch prefix:** `fix` — the majority of the change is defect repair in shipped readers, guards and
the contracts that describe them; no new capability is added.

## Problem

Three families of defect share one shape across the metrics, change-ledger and timestamp surfaces:
**an absence, an exclusion, or a suppressed caveat is rendered as a measurement.** Each was found by
verification of an already-landed plan in this epic, and each still reproduces at HEAD.

**Ratios and counts computed from nothing.** `_sequence_build_minimality_plan`
(`.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`) gates its `build_share` on the
*denominator* only — `total_build_seconds / wall_clock_seconds if wall_clock_seconds > 0 else None` —
so a plan with **no ledger rows at all** (numerator `0` by absence, which the check's own document
tells the reader to read as "UNAVAILABLE, absent is not zero") gets a fabricated `0%` share stamped
`informational`, contradicting the `has_ledger: false` cell of its own row. On the same file,
`_classify_zero` reads a `preference-pattern-detector` zero as `disciplinary` — "the corpus was
clean" — when the block's own `unattributed_excluded_count` says a gate declined every qualifying
tuple. And `summarize_build_ledger`
(`marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py`) tallies an
`unknown` build status internally and then omits it from the block it returns, so
`pass + error + timeout + killed` can be strictly less than `build_count` with nothing naming the
remainder; the audit check's per-plan row has the same hole while its corpus totals do not.

**Guards that cannot observe the defect they name.** The display-timezone plan's `⛔`-marked
storage invariant test asserts `now_utc_iso().endswith('Z')` — but the `Z` is a literal inside
`strftime('%Y-%m-%dT%H:%M:%SZ')` at
`marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py`, so it survives any
timezone conversion. Its sibling write-path guard
(`test/plan-marshall/manage-run-config/test_display_timezone_guard.py`,
`test_knob_symbols_never_reach_a_store_or_compare_site`) exempts declared RENDER *files* whole, and
both exempted files contain persisted-timestamp writes; the mitigation its own run report cited —
"the granularity is documented in the classification artifact" — was never written.

**Contracts that describe a reader that no longer behaves that way.** The dispatch-boundary cell-read
table, the lock-step "four restating surfaces" lists, the eleven-row build-status consumer table, the
`kind=build` stamp predicate, two test names asserting a retired three-state model, and one unmarked
category-B shim all state something the code contradicts. Each is a text whose whole value is what a
later maintainer *does* with it.

## Goal

Every surface in this plan that reports a build count, a build share, a timestamp provenance verdict
or a schema contract either carries the measurement it claims or names the absence explicitly — and
the two guards that were supposed to keep the display-timezone knob off the write path can, when
mutated, actually see the leak they exist to prevent. The contract documents a maintainer reads before
changing any of these describe the shipped behaviour rather than a superseded one.

## Deliverables

Ordered so the three `high` gaps land in D2 and D3. **D1 is a cheap gating derivation** (three
searches, recorded in the run report) that must run first because D5 and D8 rest on the populations
it produces; if a population cannot be derived, D1 does **not** invent a fallback list.

1. **D1 — Derive the three scoping populations, or stop the deliverables that rest on them**
   *(gates D5 and D8 — closes no gap by itself)*
   Re-derive, at the commit the run is on, and record each result **with the exact command used** in
   the run report:
   - **(a) the timestamp population** — every file under `marketplace/bundles/**/*.py` that reaches
     `now_utc_iso` or `format_timestamp`, and the subset of those that match the `scan_regex` already
     stored in `test/plan-marshall/manage-run-config/timestamp_render_classification.json`. The
     difference is the blind spot D8(a) closes.
   - **(b) the ledger build-status consumer set** — every module under `marketplace/bundles/` that
     imports `read_entries` from `_ledger_core` *and* filters on `kind == 'build'`. This is the
     derivation method the eleven-row table in
     `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md`
     declares for itself.
   - **(c) the `--plan-id` declaring `manage-*` scripts**, under **both** CLI construction shapes —
     `.add_parser(` / `add_plan_id_arg(` / `add_argument('--plan-id'` / `add_body_consumer_args(`,
     **and** the declarative `create_workflow_cli(` subcommand literals (`'name':` keys and
     `'flags': ['--plan-id']`).

   ⛔ **Do not hand-maintain any of these lists.** If a derivation cannot be run or returns something
   the plan's premise contradicts, record the failure and its evidence in the run report, skip the
   dependent deliverable, and mark the plan **partial** — a hand-written substitute reproduces the
   very defect these deliverables close. D2, D3, D4, D6, D7 and D9 do **not** depend on D1 and
   proceed regardless.
   *Done when:* the run report carries all three populations as re-derived lists, each beside the
   verbatim command that produced it, and names any that could not be derived.

2. **D2 — The display-timezone guards observe the defect they name** *(closes 150/G1, 150/G5 — both
   `high`, both vacuous-guard: RED-FIRST REQUIRED)*
   - **(a)** Rewrite `test_stored_timestamp_is_utc_under_any_knob_value`
     (`test/plan-marshall/manage-run-config/test_display_time_render.py`) to assert the **digits**,
     not the `Z` literal: freeze the clock by monkeypatching `file_ops.datetime` and assert the exact
     expected string, or parse the produced stamp and compare it against an independently computed
     `datetime.now(UTC)`. Add the same shape for the lesson-identifier prefix derivation at
     `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/manage-lessons.py`
     (`now = datetime.now(UTC)` → `date` / `hour` → `prefix`), whose date and hour digits visibly move
     under a converted clock.
   - **(b)** Tighten `test_knob_symbols_never_reach_a_store_or_compare_site`
     (`test/plan-marshall/manage-run-config/test_display_timezone_guard.py`) from file-granular to
     **site-granular** for declared RENDER files: add a `render_call_budget` integer to each
     `render_sites` entry in `timestamp_render_classification.json` and assert
     `text.count('render_timestamp(') == budget` per RENDER file instead of exempting the file
     wholesale. Re-derive each budget from the tree — do not copy a number from this plan.
   *Done when:* **each mutation below turns its guard RED and the guard is confirmed GREEN on the
   unmutated tree, with both observations recorded in the run report**, and every mutation is
   reverted (verify by `git status --porcelain` being clean on those files before commit):
   - rewriting `file_ops.now_utc_iso` as
     `datetime.now(UTC).astimezone(ZoneInfo('Asia/Kolkata')).strftime('%Y-%m-%dT%H:%M:%SZ')` turns
     D2(a)'s test RED;
   - routing the `totals_sampled_at` write in
     `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` through
     `render_timestamp(...)` instead of `now_utc_iso()` turns D2(b)'s guard RED.

3. **D3 — `audit.py` stops reading an absence or a gate-exclusion as a measurement**
   *(closes 220/G1 `high`, 410/G3, 220/G3)*
   In `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py`:
   - **(a)** Gate `build_share` in `_sequence_build_minimality_plan` on the **numerator's**
     availability as well as the denominator's — the `has_ledger` value the same function already
     derives — so a plan with no ledger rows yields `None` and the emitted cell reads `n/a`. Extend
     `checks/sequence-and-build-minimality.md` § "Build time vs plan wall-clock (share + the
     invariant)" and its `build_share` row in the column table to state that the share is withheld
     when **either** side is unavailable.
   - **(b)** Add a `_ZERO_GATED` class beside the existing `_ZERO_*` constants with an entry in
     `_ZERO_READINGS` reading, in substance, *"the check examined a non-empty population and a
     declared gate declined every qualifying row — this zero is evidence about the gate, not about
     the corpus"*; have `_classify_zero` return it when the block carries a non-zero
     `unattributed_excluded_count` and `genuine_signal_count == 0`, ordered after the
     `structural` / `no_count` / `starved` branches and before the `disciplinary` fallthrough; count
     it in `emit_suspect_zero_census_block`'s class tally.
   - **(c)** Reconcile the file's own prose to the ledger re-base: in the module docstring's
     `sequence-and-build-minimality` bullet, replace the "classifies every `pyproject_build run` by
     duration" claim with the ledger-derived description and append the `suspect_build_duration` and
     `build_exceeds_wallclock` flags; in the check's section comment, delete the sentence naming
     `.plan/temp/sequence_analysis.py` + `.plan/temp/build_minimality.py` as prototypes (those paths
     are machine-local and absent from this clone — **do not go looking for them**; they are only to
     be deleted from the comment), point instead at the "build-time ORACLE" block already present in
     the same file, and add the two missing flags to the anti-pattern catalogue.
   *Done when:* a test staging a plan with `metrics_phases` present and no ledger builds asserts
   `row['build_share'] is None` and that the emitted cell reads `n/a`, **and that test is observed
   RED against the pre-fix code**; a test asserting `_classify_zero` returns a class other than
   `disciplinary` for a block with `plans_in_corpus > 0`, `unattributed_excluded_count > 0` and
   `genuine_signal_count: 0` is likewise observed RED first, with the existing `disciplinary` /
   `starved` / `structural` tests still passing unchanged; and searching `audit.py` for
   `pyproject_build run` returns only `_sbm_is_build`'s own delta-baseline comment while
   `.plan/temp/build_minimality` returns nothing.

4. **D4 — Every build-status surface accounts for the undetermined build**
   *(closes 220/G2, 430/G8, 220/G7, 220/G6)*
   - **(a)** `summarize_build_ledger` in
     `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` already
     tallies `unknown` internally and drops it from the returned dict. Add it to the returned block
     under the field name **`status_unknown`** (see Notes → *Two naming conflicts resolved*), and
     document the field plus the identity
     `pass + error + timeout + killed + status_unknown == build_count` in the `build_time` block of
     `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/log-analysis.md`.
   - **(b)** Add a `status_unknown` column to the per-plan `rows[N]{…}` header and the matching cell
     list in `emit_sequence_build_minimality_block` (`audit.py`), between `killed` and
     `total_build_seconds`, sourced from the `build_status_unknown` the row already computes. Add the
     row to the column table in `checks/sequence-and-build-minimality.md` and restate the identity
     there at **row** scope.
   - **(c)** In
     `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/plan-efficiency.md`,
     promote the existing standalone absent-is-not-zero paragraph into the *"Two truthfulness rules
     ride with it"* list as a third rule (renaming the list accordingly), and annotate the
     `totals.total_build_seconds` line of the TOON fragment shape with the rendering rule —
     `unavailable`, never `0`, when `log_analysis.build_time.build_count == 0`. See Notes for what is
     already present at HEAD and therefore not owed.
   *Done when:* a test in `test/plan-marshall/plan-retrospective/test_analyze_logs.py` stages a build
   carrying an unrecognised status and asserts the five-term identity above; a test in
   `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_sequence_and_build_minimality_ledger_facets.py`
   stages one plan with an unrecognised build status, asserts `status_unknown` appears in the emitted
   `rows[…]{…}` header and asserts the row-scope identity; **both tests are observed RED against the
   pre-fix code**; and `plan-efficiency.md`'s TOON `totals.total_build_seconds` line carries the
   `unavailable` rendering note.

5. **D5 — The ledger build-status consumer set and the contracts that describe it**
   *(closes 430/G7, 430/G1, 430/G5, 110/G1 — needs D1(b))*
   - **(a)** Extend the consumer table in
     `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md`
     (§ "the list a change to the vocabulary must walk") so that **every member of the population
     D1(b) derived has a row**, naming each one's surface — the missing one is
     `plan-retrospective analyze-logs`, which reads the ledger `kind=build` `status`. ⚠ The table's
     existing rows are a **superset** of D1(b): it deliberately also carries second-order consumers
     that read a *freshness verdict* or an orchestrator-obtained build outcome rather than importing
     the ledger at all, and the paragraph below the table says so. **Retain every existing row** —
     D1(b) is a completeness floor, not a replacement list. In the same edit, state the derivation
     command beside the table so the next reader re-runs it rather than trusting the row count.
     **Write no population number that was not re-derived in this run.**
   - **(b)** Correct the stale pre-fix rule in the module-level comment block above
     `test_build_boundary_stamps_derived_status`
     (`test/plan-marshall/tools-script-executor/test_executor_runtime.py`): a stdout `killed` claim at
     exit 0 is **believed** (the wrapper's first-hand observation of the child it reaped, exactly like
     its `timeout` claim); only `unknown` is derived-only; and a stdout `indeterminate` claim at exit
     0 stamps `unknown`. Leave the correct statement in
     `marketplace/bundles/plan-marshall/skills/ref-code-quality/standards/error-handling.md`
     untouched.
   - **(c)** Add an `error` arm to `cmd_classify_outcome`'s verdict chain in
     `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py`,
     returning a verdict distinct from `undecidable` with a message naming the reported failures, and
     extend the `undecidable` docstring and the `manage-change-ledger` SKILL's classify-outcome
     section accordingly. ⛔ **Do not retire the verb** — the gap offers retirement as an alternative,
     and a lifecycle decision of that size is not one this run may take; if retirement looks right,
     record it as a **proposal** in the run report and ship the `error` arm.
   - **(d)** In `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md` § Entry
     Shapes, state the `kind=build` stamp predicate as the **three-way** conjunction the boundary
     implements — a `build-*` notation, the build-executing `run` verb, and no help spelling anywhere
     in argv — extend the suppression list beyond "a bare `--help` dispatch" to include `run --help`
     and `run -h`, and say plainly that `_is_build_class_notation` is only two of the three conjuncts,
     `_mentions_help` being the third.
   *Done when:* every member of D1(b)'s derived set has a row in the consumer table, no pre-existing
   row was removed, and the table names the command that derives its ledger-importing members;
   searching `test_executor_runtime.py` for `derived-only` returns no
   line claiming a stdout `killed` claim stamps `error`; `classify-outcome` over a ledger whose latest
   matching row carries `status: error` returns a verdict distinguishable from the one it returns for
   `status: unknown`, pinned by a test in `test/plan-marshall/manage-change-ledger/`; and
   `manage-change-ledger/SKILL.md` names all three conjuncts, lists `run --help` among the
   no-row dispatches, and contradicts nothing in `build-systems-common.md`'s three-way statement.

6. **D6 — The dispatch-boundary reader contract stops describing a reader that does not exist**
   *(closes 460/G1, 460/G2, 420/G2, 420/G3, 420/G1, 460/G4)*
   - **(a)** 460/G1 and 460/G2 edit the same two paragraphs and **must land in one commit** or the
     mirror is false in between. In `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`
     § "Restating surfaces (lock-step obligation)" and in the mirrored `LOCK-STEP OBLIGATION` comment
     above `_LEGACY_COLUMN_COUNT` in `analyze-logs.py`: raise the surface count from four to
     **five**, add `.claude/skills/audit-archived-plan-retrospectives/checks/billing-composition.md`
     as the fifth (noting, as the audit-script surface already does, that it lives outside the crawled
     inventory so a content sweep will not find it), and bring the mirror's description of the
     audit-script surface into line with the standard's — naming
     `_parse_dispatch_boundary_totals`'s cell read and the row-level provenance gate beside the two
     hand-copied constants.
   - **(b)** In `data-format.md` § Per-Dispatch Context-Load Attribution, drop `or a column the row
     does not have` from the *unrecognised* row of the cell-read table and add a distinct row mapping
     "a column the row is too short to have" to **unmeasured**, with the reason (a row written before
     the columns existed recorded no measurement). Make the same correction in
     `_parse_dispatch_boundary_file`'s docstring in `analyze-logs.py`, leaving its existing
     legacy-row sentence to own the short-row case.
   - **(c)** Replace the byte-identity sentence under the format example in `data-format.md` so it
     names a pair of representations that genuinely are byte-identical — an all-zero pre-token row
     against an all-measured-zero row — and cross-references § *Provenance of a measured zero*.
   - **(d)** Rename the two stale retrospective-reader tests in
     `test/plan-marshall/manage-metrics/test_record_model_representability.py` to mirror the already-
     renamed audit-side sibling (see Notes → *Two naming conflicts resolved* for which naming to
     take), reword the neighbouring "the third point of the three-way distinction" comment to say
     what the row demonstrates rather than counting states, and add to the composed round-trip test
     an assertion that `indeterminate_columns == []` on every row of its fixture, so the test asserts
     the state its new name claims. No assertion is removed and no fixture changes.
   *Done when:* both lock-step lists say five surfaces and both name the check doc, and a search for
   "four surfaces" / "FOUR surfaces" across the two files returns nothing; no sentence in
   § Per-Dispatch Context-Load Attribution or in either reader docstring assigns the short-row case to
   *unrecognised*; a search for `three_ways` / `three-way distinction` across
   `test/plan-marshall/manage-metrics/` returns nothing except the unrelated `metrics.toon`
   old-schema comparison (which requires a case-insensitive search to match at all); and the
   `manage-metrics` representability suite passes.

7. **D7 — The two dispatch-boundary readers resolve columns the same way** *(closes 460/G3)*
   `_parse_dispatch_boundary_totals` in `audit.py` resolves the four context-load columns **by name
   from the declared `rows[]{…}:` header**; `_parse_dispatch_boundary_file` in `analyze-logs.py`
   resolves them **positionally** and ignores the header. Adopt the header-name strategy with a
   positional fallback — the strictly more informative of the two, already implemented on the audit
   side — in `analyze-logs.py`, so the same bytes yield the same measured set and the same
   datability verdict in both readers. ⛔ **The strategy choice is made here; the run does not
   re-open it.**
   *Done when:* one shared fixture per divergence class in
   `test/plan-marshall/manage-metrics/test_record_model_representability.py` drives **both** readers
   and both report the same measured set and the same datability verdict, for all four classes: a
   short header with long rows; a malformed `total_tokens` beside a nonzero context cell; a missing
   `rows[]{…}:` header line; and a header that reorders two context columns. Each fixture is observed
   RED against the pre-fix `analyze-logs.py` before the fix lands.

8. **D8 — Population, inventory and documentation corrections**
   *(closes 150/G2, 150/G4, 050/G6, 060/G1 — 150/G2 and 060/G1 need D1(a) and D1(c))*
   - **(a)** *(150/G2)* Extend `scan_regex` in
     `test/plan-marshall/manage-run-config/timestamp_render_classification.json` to match
     `now_utc_iso` and `format_timestamp`, and reword `_description` and `_population_source` so they
     state what the regex actually covers instead of "every timestamp call site in
     `marketplace/bundles/**/*.py`". Classify the three plan-named surfaces the old regex could not
     see — the work-log renderer in `manage-logging/scripts/plan_logging.py`, the inbox listing in
     `plan-orchestrator/scripts/_orchestrator_inbox.py`, and the operator-facing summaries in
     `plan-orchestrator/scripts/orchestrator.py` — as explicit entries with a recorded verdict and
     reason, so the classification is stated rather than inferred from absence. **Re-derive every
     census figure from D1(a); write no count carried in from a gap document.**
   - **(b)** *(150/G4)* In
     `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`
     § "Generated Report (metrics.md)", add the `Generated:` line to the worked example and one
     sentence stating it renders through the display-only timezone — UTC-suffixed by default,
     `ABBREV (UTC±HH:MM)`-labelled when converted — cross-referencing
     `manage-run-config/standards/run-config-standard.md` § "Display-Timezone Section", mirroring the
     wording already used in `plan-retrospective/references/report-structure.md`.
   - **(c)** *(050/G6)* Add a conforming `# SHIM(B):` marker block immediately above the
     `posture_cutoff_legacy_aggregate` entry of `_REMOVAL_CAUSE_PATTERNS` in
     `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py`
     — `shim-owner: plan-retrospective`; `shim-floor:` the composer change that replaced the aggregate
     `lane_resolution` line with one line per dropped step; `shim-remove-when: no archived plan's
     decision log carries the aggregate lane_resolution line shape`. The convention is at
     `marketplace/bundles/pm-plugin-development/skills/plugin-script-architecture/standards/shim-marker-convention.md`.
   - **(d)** *(060/G1)* In
     `doc/plans/truthful-signals/060-invented-plan-scoping-flags-are-an-overgeneralized-convention/report-01.md`
     § D1(b) — **plan 060's own deliverable label, not this plan's** — re-derive the population from
     this plan's D1(c) covering **both** construction shapes; state beside
     the numbers which shapes the counts cover (keeping the existing parser-nodes-vs-leaf-verbs hedge,
     which is about a different thing); add the plan-scoped `manage-locks` scripts to the enumeration;
     add `manage-change-ledger`'s non-plan-scoped verbs to the carve-out table under a
     ledger/worktree-state scope row and correct the `manage-change-ledger` sentence to say it does
     declare `--plan-id` on `append` through a different construction shape; and make the
     `manage-maven-profiles` cell use the same `(parsers, plan-id)` form the other cells use.
   *Done when:* the guard's published census in
   `test_classification_covers_the_live_population_and_is_non_empty` includes every bundle `*.py`
   reaching `now_utc_iso`, and the set difference between D1(a)'s two lists is empty; the
   `manage-metrics` data-format doc mentions `display_timezone` and its worked example shows the
   `Generated:` line; the `posture_cutoff_legacy_aggregate` entry carries a marker with all three
   fields non-empty **and** running `analyze_shim_marker(Path('marketplace/bundles'))` reports no
   finding naming `check-routing-decisions.py` (it reports none today, so this checks the new marker
   is well-formed, not that a finding cleared — see Notes); and `060`'s § D1(b) names every `manage-*`
   script declaring `--plan-id` under either shape, with the carve-out table carrying the three
   `manage-change-ledger` verbs.

9. **D9 — Resolve the `CHECK_ERA` boundary for the checks this plan re-bases** *(closes no gap; a run
   obligation this plan carries because the lane contract does not)*
   D3 and D4(b) change the semantics of the `sequence-and-build-minimality` check, so archived rows
   must be datable against a boundary. While working, set that check's entry in the `CHECK_ERA` table
   in `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` to the literal
   `PR-PENDING` sentinel with a comment naming what this plan changed. **After create-pr and before
   the merge gate**, resolve it by running
   `python3 .claude/skills/finalize-step-era-stamp-fill/scripts/era_stamp_fill.py run --pr-number {N} --worktree-path .`
   and commit and push the result. That step rewrites `audit.py` and its lock-step test mirror
   `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_era_model.py` together.
   ⛔ The finalize step that normally does this **does not fire in this lane** — it must be run by
   hand. If it fails, do **not** land a literal `PR-PENDING` on `main`: report the run blocked at the
   merge gate.
   *Done when:* no `PR-PENDING` value remains in `CHECK_ERA` (the word may still appear in explanatory
   comments), `sequence-and-build-minimality`'s entry names this PR's number, and
   `test_audit_check_era_model.py` passes.

## Out of scope

- **Every other gap in the nine source `gaps.md` files.** Each is assigned to a different plan in
  this epic's fix-out wave; picking one up here would duplicate work already numbered elsewhere and
  would put two plans on the same paragraph.
- **`220/G4` and `410/G2`.** Both require corpora that live only under `.plan/` —
  `work/change-ledger.jsonl`, `local/archived-plans/`, `project-architecture/default/enriched.json`.
  `.plan/` is git-ignored, so a cloud clone has none of it. ⛔ **Do not go looking for those paths**;
  they are named here only so the run recognises them as unreachable rather than missing.
- **`220/G5` — amending `.claude/skills/cloud-plan-lane/SKILL.md` to carry the `CHECK_ERA`
  obligation.** That is the contract governing this run, and a run may not self-approve a change to
  its own governing contract. D9 discharges the obligation for *this* run inline; if the run judges
  the contract should carry it permanently, it records that as a **proposal** in the run report.
- **`430/G2` and `430/G3` — the missing `indeterminate` wire row and the vocabulary-totality test.**
  Those change the build daemon's wire protocol and terminalization behaviour, a far wider blast
  radius than this plan's reader-and-reporting surface, and they are not in this plan's gap set. A
  hang in the daemon is a worse failure than the reporting defects here, so it gets its own plan.
- **`150/G3` — routing `display_timezone` from the marshall-steward configuration submenu.** Not in
  this plan's gap set, and it is a UI-surface addition rather than a truthfulness repair; grouping it
  here would put a menu-flow change in a plan whose verification is entirely about measurement
  honesty.
- **Seeding `display_timezone` into `DEFAULT_STRUCTURE`** in
  `manage-run-config/scripts/run_config.py`. Explicitly refuted by plan 150's adversarial review:
  *every* optional run-config section is unseeded, so seeding this one alone would make it the sole
  exception to a uniform convention, and changing that convention is a file-wide policy decision this
  plan has no operator to take.
- **Retiring `manage-change-ledger classify-outcome`.** D5(c) fixes the misreport; retiring a verb is
  a lifecycle decision, and with no operator to confirm it the run would be deciding on the project's
  behalf.
- **`/sync-plugin-cache` or any refresh of `~/.claude/`.** Inert in this lane: it is a machine-local
  build step reading a git-ignored `target/` tree that a fresh clone does not have. The merged bundle
  source is authoritative.

## Expected surface

Files this plan is expected to touch. **Re-derive rather than trust this list** where a deliverable's
scope comes from D1 — it is an authoring-time expectation, not a measurement.

- `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` — D3 (build_share gate,
  `_ZERO_GATED`, docstring + section comment), D4(b) (row column), D9 (`CHECK_ERA`).
- `.claude/skills/audit-archived-plan-retrospectives/checks/sequence-and-build-minimality.md` —
  D3(a) withholding rule, D4(b) column table + row-scope identity.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/analyze-logs.py` — D4(a)
  `status_unknown`, D6(a) lock-step mirror, D6(b) docstring, D7 column resolution.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/log-analysis.md` — D4(a)
  field + identity.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/plan-efficiency.md` —
  D4(c) third truthfulness rule + TOON annotation.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py` —
  D8(c) shim marker.
- `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — D6(a)(b)(c),
  D8(b).
- `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/manage-change-ledger.py` and
  `.../manage-change-ledger/SKILL.md` — D5(c), D5(d).
- `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-systems-common.md` —
  D5(a) consumer table.
- `test/plan-marshall/manage-run-config/test_display_time_render.py`,
  `.../test_display_timezone_guard.py`, `.../timestamp_render_classification.json` — D2, D8(a).
- `test/plan-marshall/audit-archived-plan-retrospectives/test_audit_check_sequence_and_build_minimality_ledger_facets.py`
  and `.../test_audit_check_era_model.py` — D3, D4(b), D9.
- `test/plan-marshall/plan-retrospective/test_analyze_logs.py` — D4(a).
- `test/plan-marshall/manage-metrics/test_record_model_representability.py` — D6(d), D7.
- `test/plan-marshall/tools-script-executor/test_executor_runtime.py` — D5(b) comment.
- `test/plan-marshall/manage-change-ledger/test_classify_outcome.py` — D5(c).
- `doc/plans/truthful-signals/060-invented-plan-scoping-flags-are-an-overgeneralized-convention/report-01.md`
  — D8(d).
- Touched only under a **mutation that must be reverted** (D2's red-first checks):
  `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` and
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py`.

## Claim labels

Every premise below was checked against the tree while authoring, at the commit this plan was written
on. **Each artifact is git-tracked and reachable from a fresh clone** — including
`.claude/skills/audit-archived-plan-retrospectives/`, which is git-tracked even though it is outside
the architecture inventory's crawl.

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| 150/G1 (`high`) reproduces: the D6(c) test asserts only the `Z` suffix, a literal inside the format string | OBSERVED | `test/plan-marshall/manage-run-config/test_display_time_render.py` → `test_stored_timestamp_is_utc_under_any_knob_value`; `.../tools-file-ops/scripts/file_ops.py` → `now_utc_iso` |
| 150/G5 (`high`) reproduces: the guard's `allowed` set is file-granular, and neither `_guard_granularity` nor `render_call_budget` exists in the classification artifact | OBSERVED | `test/plan-marshall/manage-run-config/test_display_timezone_guard.py` → `test_knob_symbols_never_reach_a_store_or_compare_site`; `.../timestamp_render_classification.json` (asserted absence, verified by searching the file for both key names) |
| 220/G1 (`high`) reproduces: `build_share` is gated on `wall_clock_seconds > 0` alone | OBSERVED | `.claude/skills/audit-archived-plan-retrospectives/scripts/audit.py` → `_sequence_build_minimality_plan`, the `build_share` expression |
| 220/G2 + 430/G8 reproduce and are the **same site**: `summarize_build_ledger` tallies `unknown` and omits it from its return dict | OBSERVED | `.../plan-retrospective/scripts/analyze-logs.py` → `summarize_build_ledger` |
| 220/G7 reproduces: the per-plan `rows[N]{…}` header carries no `status_unknown` column while `corpus_build_status_unknown` is emitted | OBSERVED | `audit.py` → `emit_sequence_build_minimality_block` |
| 410/G3 reproduces: `_ZERO_GATED` does not exist and `_classify_zero` never consults `unattributed_excluded_count` | OBSERVED | `audit.py` → `_ZERO_DISCIPLINARY` / `_classify_zero` / `_ZERO_READINGS` (asserted absence, verified by searching the file for `_ZERO_GATED`) |
| 430/G7 reproduces: the consumer table has eleven rows and no `analyze-logs` row | OBSERVED | `.../extension-api/standards/build-systems-common.md` § "the list a change to the vocabulary must walk" |
| 420/G1 + 460/G4 reproduce and name the **same three sites** | OBSERVED | `test/plan-marshall/manage-metrics/test_record_model_representability.py` — the comment and the two `…_reads_three_ways_in_the_retrospective_reader` test names |
| 420/G2, 420/G3, 460/G1, 460/G2 reproduce | OBSERVED | `.../manage-metrics/standards/data-format.md` (cell-read table's *unrecognised* row; the byte-identity sentence under the format example; § "Restating surfaces") and the `LOCK-STEP OBLIGATION` comment in `analyze-logs.py` — neither list names `checks/billing-composition.md` |
| 460/G3 reproduces: the two readers use name-resolution and positional resolution respectively | OBSERVED | `audit.py` → `_parse_dispatch_boundary_totals` (`columns.index(ledger_field)`) vs `analyze-logs.py` → `_parse_dispatch_boundary_file` (`_LEGACY_COLUMN_COUNT + offset`) |
| 430/G1, 430/G5, 110/G1, 050/G6, 060/G1, 150/G2, 150/G4, 220/G3 reproduce | OBSERVED | respectively: the `derived-only` comment in `test_executor_runtime.py`; `cmd_classify_outcome`'s verdict chain with no `error` arm; the two-way conjunction in `manage-change-ledger/SKILL.md` § Entry Shapes vs the three-conjunct `if` in `execute-script.py.template`; the marker-free `posture_cutoff_legacy_aggregate` entry; `manage-locks` absent from `060`'s `report-01.md`; `scan_regex` in the classification JSON matching neither `now_utc_iso` nor `format_timestamp`; `display_timezone` absent from `manage-metrics/standards/data-format.md`; the `pyproject_build run` docstring claim and the `.plan/temp/` prototype sentence in `audit.py` |
| 220/G6 is **partially closed at HEAD**: the absent-is-not-zero sentence already exists; the TOON annotation and the third-rule placement do not | OBSERVED | `.../plan-retrospective/references/plan-efficiency.md` § "Build time is READ from the change-ledger" carries the sentence; the `totals.total_build_seconds` line of the TOON fragment carries only the FLOOR note. The sentence landed with plan 220 itself (`8620ab0b`, PR #1224) |
| D8(c)'s Done-when as the gap wrote it is **vacuous**: the shim analyzer already reports zero findings tree-wide, so "returns `[]`" holds before and after | OBSERVED | running `analyze_shim_marker(Path('marketplace/bundles'))` from `.../plugin-doctor/scripts/_analyze_shim_marker.py` returned `0` findings while authoring; re-derive it in the run rather than trusting this |
| The three D1 populations are derivable by search alone, with no `.plan/` state | HYPOTHESIS | D1 itself settles it: each derivation is a search over `marketplace/bundles/` — a git-tracked tree present in every clone. If one fails, D1's stop condition fires and the dependent deliverable is skipped |
| The expected surface above is complete | HYPOTHESIS | The pre-PR verification sub-agent's collateral-change check against the actual diff. A file appearing in the diff that is not listed above is reported, not silently accepted |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half. The
three absences this plan rests on — `_guard_granularity` / `render_call_budget`, `_ZERO_GATED`, and
`checks/billing-composition.md` in either lock-step list — were each verified by searching the named
file for the named string, not inferred.

## Verification

Beyond every deliverable's own *Done when*:

1. **Red-first is mandatory, and is reported.** Every test this plan adds or rewrites in D2, D3, D4
   and D7 must be **observed RED against the pre-fix code** before the fix lands, and the run report
   records for each one what it was run against and what it printed. A test that was never seen red
   against the defect it names does not close its gap — it is the exact defect class two of these
   gaps are.
2. **Mutations are reverted and the revert is proven.** D2's two mutations touch shipped source. After
   each red-first observation, restore the file and confirm the working tree is clean on it before
   any commit. A mutation that reaches `main` is worse than the defect it was probing.
3. **Four cold reads of text-that-drives-a-reader.** Dispatch an independent reader — one that has
   not seen this plan — at each of the following, ask it what the text tells it to DO, and record
   **which reading it took** in the run report. A wrong reading means the wording failed, however
   complete it looks:
   - **The cell-read table** (D6(b), `data-format.md` § Per-Dispatch Context-Load Attribution): *"You
     are implementing a new reader of this artifact from this section alone. A row carries only five
     columns. What do you report for the four context-load columns?"* The required reading is
     **unmeasured**. If it answers *unrecognised*, D6(b) has not landed.
   - **The consumer table** (D5(a), `build-systems-common.md`): *"The build-status vocabulary is
     changing. Using only this page, list every consumer you must walk, and say how you know the list
     is complete."* The required reading names the derivation command and every member of D1(b) —
     not a memorised count.
   - **The `plan-efficiency.md` build-time rule** (D4(c)): *"A plan's `build_time` block reports
     `build_count: 0`. What do you print for `total_build_seconds` in report §7?"* The required
     reading is **`unavailable`**, never `0`.
   Additionally read back **`_ZERO_READINGS[_ZERO_GATED]`** (D3(b)) cold: *"An audit block carries
   this class and this reading. What does it tell you about the corpus?"* The required reading is
   that it says nothing about the corpus — it is evidence about a gate.
4. **Full suite green.** The change touches Python under `marketplace/bundles/`, `.claude/skills/` and
   `test/`, so the build gate applies: run the project's verify and report its outcome. In addition,
   run at minimum the directly affected suites —
   `test/plan-marshall/manage-run-config/`, `test/plan-marshall/audit-archived-plan-retrospectives/`,
   `test/plan-marshall/plan-retrospective/`, `test/plan-marshall/manage-metrics/`,
   `test/plan-marshall/manage-change-ledger/`, `test/plan-marshall/tools-script-executor/` — and
   record pass counts **re-derived at the moment of the claim**, never carried from this plan.
5. **Lock-step landing.** D6(a)'s two edits (the standard's list and the mirror comment) must be in
   the same commit. Verify by reading the commit's file list, not by intending it.
6. **Per-gap coverage read-back.** Before the merge gate, walk the twenty-four gap ids in the
   Deliverables headings against the diff and state, per id, closed / partial / not attempted. A
   partial is reported as partial; an overstated outcome is collected as done and never picked up
   again.

## Notes

**Where the gaps came from.** Every gap this plan closes is recorded in a git-tracked
`doc/plans/truthful-signals/{plan-dir}/gaps.md`, alongside a `verification.md` whose
`## Adversarial review` section records which gaps were upheld, refuted, re-severitied or added.
**Where a gap body and that section disagree, the adversarial-review section wins.** The nine source
directories are `050-migration-shims-have-no-expiry`,
`060-invented-plan-scoping-flags-are-an-overgeneralized-convention`,
`110-landed-residue-promotion-sweep`, `150-configurable-display-timezone-for-rendered-timestamps`,
`220-build-ledger-is-the-build-time-oracle`,
`410-the-pipeline-talks-to-itself-and-learns-from-the-echo`,
`420-the-writer-already-destroyed-the-distinction-the-reader-learned-to-make`,
`430-a-timeout-is-not-a-red-test-and-a-kill-is-not-a-timeout` and
`460-audit-ledger-reader-reads-undatable-zero-as-measured`. Read the full entry for a gap before
implementing its deliverable — the *Why it matters* paragraph usually names the failure mode the fix
must actually prevent.

**Two naming conflicts resolved here, so the run does not have to decide.**

1. *`status_unknown` vs `unknown`.* 220/G2 asks for the omitted build-status count on
   `summarize_build_ledger`'s return dict to be named `status_unknown`; 430/G8 asks for the same
   field and calls it `unknown`. **Take `status_unknown`** — it mirrors the audit side's existing
   `build_status_unknown` / `corpus_build_status_unknown` spelling, so the identity reads the same on
   both surfaces, and it does not collide with the `unknown` key already used inside
   `status_counts`. 430/G8's spelling is superseded; nothing else in that gap changes.
2. *Which rename for the two stale test names.* 420/G1 proposes `…_reads_four_ways_…`; 460/G4
   proposes names that state the invariant instead of counting states, mirroring the audit-side
   sibling that was already renamed. **Take 460/G4's naming** — a name that counts states goes stale
   the next time a state is added, which is precisely how these two names became wrong. Keep 420/G1's
   additional requirement: the composed round-trip test gains an `indeterminate_columns == []`
   assertion so it asserts what its new name claims.

**What is already true at HEAD, and therefore not owed.** 220/G6 states that `plan-efficiency.md`
"never repeats" the absent-is-not-zero rule. That clause is **false at HEAD** — the sentence *"A plan
with `build_count: 0` has no ledger build rows — its build time is UNAVAILABLE (absent is not zero),
not 'no builds ran'"* is present in § "Build time is READ from the change-ledger", and landed with
plan 220's own commit (`8620ab0b`, PR #1224). D4(c) is therefore narrowed to what is genuinely
missing: the rule's placement inside the *"Two truthfulness rules"* list, and the `unavailable`
annotation on the TOON `totals.total_build_seconds` line. Re-check this before writing — if the
paragraph has moved, adjust rather than duplicate it.

**Sequencing against the epic.** No gap here is a defect in another plan's deliverables; all are
residue, incomplete sweeps and stale statements left behind by landed work. Nothing in this plan
depends on another `truthful-signals` plan landing first. Two files are shared with sibling fix-out
plans in the same wave — `audit.py` and `data-format.md` — so if a merge conflict appears on either,
rebase and re-read the conflicting paragraph rather than resolving it mechanically: both files carry
lock-step obligations that a textual merge will not honour.

**A machine-local path that appears in this plan's text.** `.plan/temp/sequence_analysis.py` and
`.plan/temp/build_minimality.py` are named in D3(c) **only as strings to delete from a comment**.
`.plan/` is git-ignored and absent from this clone — do not go looking for those files, and do not
treat their absence as a problem to solve.

**Counts in this document are leads.** Every number a gap document carries — the twelve blind-spot
files, the eleven consumer rows, the four surfaces, the nine persisted timestamps in
`manage-metrics.py` — was derived at some earlier commit by an agent that is not this run.
**Re-derive each at the moment you rely on it.** Where a re-derivation disagrees with a gap document,
the tree wins and the disagreement goes in the run report.
