# Verification — 340-token-ledgers-disagree-and-the-smallest-is-named-actual

**Audited:** `plan.md`, `report-01.md`, `status-report.md`
**Tree state:** `a55a9eb` on `claude/code-intelligence-substrate-analysis-kah884` (audit began at `dd1eea1`;
`git diff --stat dd1eea1 a55a9eb -- marketplace/ test/` is empty, so every citation below is stable across
the audit window). The plan landed as squash commit `85abeeb` — *fix(metrics): a token figure carries its
population or it is not named "actual" (#1293)*. The branch commits named in the report (`c39363a`,
`d52dea8`, `f97455d`, `394053d`, `4dcc65b`, `f1b9eb9`, `cf1ba0b`) are **not objects in this clone**
(`git cat-file -t` → `Not a valid object name`), so per-commit attributions are UNVERIFIABLE; the merged
content is verified instead.
**Overall verdict:** CONFIRMED WITH GAPS

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | Hard gate: re-derive the three ledgers; arithmetic blocked → writer-side derivation | Populations differ by construction; the cost-preview key has no producer; blast-radius arm closed | Every writer-side citation lands on the claimed symbol; the no-producer claim re-confirmed by whole-tree grep; the ledger corpus is absent from this clone too | CONFIRMED |
| D2 | `actual_tokens` stops being a partial; comparison population-matched | Renamed to `execution_log_tokens` + `execution_log_population`; refusal gate; 11+2+2 tests | All present; refusal gate mutation-tested red; sum filtered to `EXECUTION_LOG_PHASES`; mirror held by a contract-drift test | CONFIRMED |
| D3 | Every figure carries its population; the renderer persists what it renders | Value + `_population_count` + shared denominator per column, plus spans-populations, sampled-at, declared exclusions; `inline_main_context_tokens` completed on every row; present-iff-fresh aggregate | All fields present and persisted; round-trip and invalidation guards both mutation-tested red; no new population-vocabulary member coined in `TOKEN_POPULATIONS` | CONFIRMED |
| D4 | Deterministic cross-ledger reconciliation as a script | `reconcile-ledgers` verb + `_ledger_reconciliation.py`; both partiality shapes distinct; 19 tests | Verb, module, both shapes and the structural-exclusion / `not_evaluated` states all present and tested; the maximum-matching regression test drives red against the exact defect it names. **But** the `--help` description restates a claim round 2 refuted, and the augmenting path is provably redundant while nothing records it | PARTIAL |
| D5 | Fold an unclosed phase's boundary sum, LABELLED; keep the duration verdict | `(boundary floor)` / `(boundary sum, over-covering)`, `tokens_cell_source` persisted, duration partiality untouched; 12 tests | Exactly as claimed; the `end_time` guard, the marker discrimination, its negative control and the never-lowers rule are each mutation-tested red | CONFIRMED |
| D6 | Two derived figures whose names assert the wrong population | Arm 1: `worked_seconds_per_task` reading the worked figure, no clamping. Arm 2: `enrich` derives its field list from the canonical label set | Arm 2 confirmed in code (`_FOUR_FIELD_USAGE_FIELDS`). Arm 1 lives entirely in an LLM-read reference contract; the shipped tests verify the *substrate* (`totals_worked_ms` vs `totals_wall_ms`), which the test class docstring states outright, and nothing asserts the emitted key name | PARTIAL |
| D7 | Three tests, each verified to FAIL pre-fix | (a) per-row findings, (b) refusal, (c) missing population marker fails | (a), (b) and (c) each driven red by a targeted mutation performed in this audit | CONFIRMED |

## Per-deliverable detail

### D1 — the hard gate

- **Required (plan):** re-derive the three totals, the row-level intersection and the repeated-step counts;
  if the corpus is unreachable, derive the ledgers' *writers* and report the arithmetic re-derivation
  blocked. No other deliverable may be scoped until this is done.
- **Claimed (report):** arithmetic BLOCKED (artifacts git-ignored, absent from the clone); writer-side
  derivation decisive — the populations differ by construction; and D1 **refutes** the plan's own
  load-bearing claim that the sum is fed into a live recalibration loop.
- **Found:**
  - `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/_manifest_core.py:247`
    — `VALID_RECORD_PHASES = ('5-execute', '6-finalize')`, enforced at
    `manage-execution-manifest.py:2618` (`Invalid phase: … Must be one of …`). The `execution_log` really
    cannot hold phases 1–4.
  - `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:515-522` —
    `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` holds exactly **6** classes, re-counted from the tuple.
  - `manage-metrics.py:1364` `_worked_ms`, `:918` `write_metrics`, `:1954` the single `preserve_totals`
    call — the store spans all six phases via `PHASE_NAMES`.
  - **No producer for the prediction.** Whole-tree grep for `execution_profile_cost_preview` (excluding
    `doc/plans/` and `__pycache__`) returns only `check-routing-decisions.py` (reader + docstrings),
    `routing-decision-verification.md:70` (documentation added by this plan), and
    `test_plan_retrospective_manifest.py` (hand-seeded fixtures). Zero writers.
  - `phase-1-init/SKILL.md:924` persists `--field execution_profile` only; `cost_sum_tokens` appears at
    `:907` as an option label, never as a persisted field.
  - The candidate producer is real and phase-6-scoped:
    `manage-execution-manifest.py:1786` `'cost_sum_tokens': _sum_lane_cost(kept, table)` inside the
    `for posture in LANE_TIERS` loop over `phase_6_steps` (`:1783-1787`).
  - **Corpus genuinely absent here too:** `/home/user/plan-marshall/.plan/local/` contains only `logs/`
    and `marshall-state.toon` — no `plans/` tree. The arithmetic re-derivation is blocked in this clone
    as well, so the report's blocked verdict is independently corroborated rather than merely accepted.
- **Checks run:** `git cat-file -t` on the seven cited branch SHAs; whole-tree greps as above;
  directory listing of `.plan/local/`.
- **Verdict:** CONFIRMED. The writer-side derivation is sound, the refutation of the plan's rationale is
  correct against the current tree, and the blast-radius arm is genuinely closed (no producer ⇒ no
  recalibration can ever have run). The plan's "twice / three times / four in the union" figures remain
  **UNVERIFIABLE** — as the report itself says, and it correctly declines to cite them as results.

### D2 — the "actual" figure stops being a partial

- **Required (plan):** *Done when:* a population-mismatched comparison is refused or annotated, asserted
  by test.
- **Claimed (report):** `actual_tokens` → `execution_log_tokens` beside `execution_log_population`;
  delta only on `comparison: computed`; mismatch (including `unstated`) refused with a reason;
  11 behavioural + 2 contract-drift + 2 population-filter tests.
- **Found:** `check-routing-decisions.py:448` `EXECUTION_LOG_PHASES`, `:454` `EXECUTION_LOG_POPULATION`,
  `:463` `POPULATION_UNSTATED`, `:469-471` the three verdicts, `:474-500` `sum_execution_log_tokens`
  (filtered to the population it labels), `:622-718` `evaluate_cost_preview` with the three exits at
  `:690`, `:702`, `:713`. Contract-drift tests at
  `test/plan-marshall/plan-retrospective/test_check_routing_decisions.py:644` and `:663`; population
  filter at `:684` and `:704`.
- **Checks run:**
  - Collection: `pytest test_plan_retrospective_manifest.py -k "cost_preview or preview" --collect-only`
    → **11 tests collected**; the two drift tests and the two filter tests re-counted by reading the file.
    Every number in the report's D2 row re-derived here rather than copied.
  - **Mutation:** `if predicted_population != EXECUTION_LOG_POPULATION:` → `if False:` →
    `test_cost_preview_refuses_population_mismatched_comparison` and
    `test_cost_preview_refuses_prediction_with_unstated_population` both **FAIL**
    (`assert 'computed' == 'refused'`). The refusal gate is non-vacuous.
  - Baseline: all 141 tests across the four affected modules pass unmutated.
- **Verdict:** CONFIRMED.

### D3 — every token figure carries its population, and the renderer persists what it renders

- **Required (plan):** persist the aggregate with its population count as a field, the inline-cost field
  for every phase (or an explicit not-measured marker — never absence), and the comparator/exclusion
  semantics as data. *Done when:* no rendered figure lacks a persisted counterpart. This plan must not
  define population values.
- **Claimed (report):** each Total column persists a triple, plus
  `totals_tokens_spans_populations`, `totals_sampled_at`, `dispatch_boundary_excluded_classes`;
  `inline_main_context_tokens` completed on every row; aggregate invalidated by any non-`generate` write.
- **Found:** `manage-metrics.py:290-319` (`_TOTALS_FIELDS`, `_POPULATION_COUNT_SUFFIX`,
  `_TOTALS_DENOMINATOR_FIELD`, `_TOTALS_SAMPLED_AT_FIELD`, `_TOTALS_SPANS_POPULATIONS_FIELD`,
  `_BOUNDARY_EXCLUDED_CLASSES_FIELD`); the persist-then-render block at `:1917-1954`, with the Total row
  read back through `_total_str` at `:1956-1980`; the inline-cost completion loop at `:1595-1610`
  (`0` where `total_tokens_population` is stamped, `UNMEASURED_COLUMN_TOKEN` otherwise);
  `write_metrics`'s invalidation at `:948-957`.
- **Checks run:**
  - **Mutation:** `if not preserve_totals:` → `if False:` →
    `test_a_later_write_invalidates_the_aggregate_rather_than_stranding_it` **FAILS**.
  - **Mutation:** `= len(values)` → `= breakdown_n` → 8 tests fail across three modules, including
    `test_population_qualifier_is_persisted_not_only_rendered`.
  - **Mutation (D7c, the faithful "render the qualifier, persist nothing" mutant):** `write_metrics`'s
    key-emission filter extended to drop `*_population_count` → 4 tests fail, including
    `test_a_rendered_total_without_a_persisted_population_count_is_caught`.
  - **Vocabulary check:** `git diff 85abeeb^ 85abeeb` touches `TOKEN_POPULATIONS` on **no** line
    (only a comment referencing it was added at `:350`). The out-of-scope prohibition was respected.
  - Documentation round-trip: `data-format.md:503-527` documents every persisted field, the
    present-iff-fresh rule, the two scoping exceptions (`phase-boundary`,
    `dispatch_boundary_excluded_classes`), and the "not satisfied by parsing metrics.md" clause.
- **Verdict:** CONFIRMED. One observation, not a defect: the Total row reads the in-memory `data` dict
  that `write_metrics` was just handed rather than re-reading the file, so "the render reads the store
  back" is true of the values but not literally of a second read. Every value it prints is nonetheless
  a key written in that same call.

### D4 — a deterministic cross-ledger reconciliation

- **Required (plan):** a SCRIPT, joining on phase/step/timestamp window, one finding per row present in
  one ledger and absent from another; it must handle **both** shapes — never-closed and
  closed-then-re-entered — with the labels distinct. *Done when:* a disagreeing pair produces a per-row
  finding, and both shapes are represented in tests.
- **Claimed (report):** read-only `reconcile-ledgers` verb + `_ledger_reconciliation.py`;
  `boundary_never_closed` / `phase_re_entered` distinct from `row_absent_from_*`; structural exclusions
  declared; unreadable manifest → `not_evaluated`; publishes `union_rows`; **19 tests**; three guards
  mutation-tested; the matching brute-forced over 3 000 corpora.
- **Found:** `_ledger_reconciliation.py:89-97` (finding kinds and states), `:249-353` `pair_rows`,
  `:356-395` `_phase_findings`, `:398-481` `reconcile_phase`; the verb at `manage-metrics.py:2964-3035`
  and its parser at `:3735-3764`.
- **Checks run:**
  - Collection: `pytest test_ledger_reconciliation.py --collect-only` → **22 tests**
    (19 + the 3 in `TestMixedTimezoneAwarenessDoesNotCrash`, added by the R4-F5 reviewer fix).
  - **Mutation:** the pairing window widened to `10**9` → `test_the_window_is_a_real_bound_in_both_directions`
    and `test_the_union_is_published_per_phase_and_in_total` **FAIL**.
  - **Mutation:** `_row_sort_key`'s three tie-breakers neutralised →
    `test_which_rows_are_reported_does_not_depend_on_input_order` and
    `test_the_sort_key_is_total_over_the_rows_own_values` **FAIL**.
  - **Mutation that SURVIVES:** `if holder is None or _augment(holder, visited):` → `if holder is None:`
    (i.e. maximum matching degraded to plain first-fit greedy) → **22 passed**. The R3-F6 regression
    test does not fail against it, because the fix's actual mechanism is not what that corpus
    distinguishes.
  - **Characterisation:** over **5 000 random corpora** (0–6 rows per side, windows 60/300/600 s), a
    first-fit greedy in the module's own sort order produced a matching of the same size as `pair_rows`
    in **5 000/5 000** cases. The eligibility sets are contiguous index intervals with monotone
    endpoints, for which first-fit in sorted order is already maximum — so the augmenting path cannot
    change the result on this input shape, and no in-tree test could distinguish the two. See G2/G3.
  - **F18 re-checked:** whole-tree grep for `reconcile-ledgers` (excluding `doc/plans/` and
    `__pycache__`) → `SKILL.md` ×3, `manage-metrics.py` ×3 (usage banner, parser, `set_defaults`),
    `test_ledger_reconciliation.py:68`, and the generated executor's surface registry. **Zero workflow
    call sites.** The residue is still open.
- **Verdict:** PARTIAL. The deliverable's literal *Done when* is met, but two things fall short of the
  report's account: the maximality that R3-F6 introduced is unpinned by any shipped test (G2), and the
  verb's `--help` description restates a claim round 2 refuted (G1).

### D5 — fold a recorded-but-unclosed phase's boundary sum into its cell, LABELLED

- **Required (plan):** fold when a phase has no `end_time` but does have a dispatch-boundary file, as a
  **labelled** figure; keep the partiality verdict for duration.
- **Claimed (report):** `(boundary floor)` where coverage is partial/undecidable, `(boundary sum,
  over-covering)` where the file holds more rows than sampled dispatches, with matching
  `tokens_cell_source`; fires both where the sum was refused and where it silently won; duration
  untouched; 12 tests (7 fold + 5 over-covering).
- **Found:** `manage-metrics.py:618-658` `_unclosed_boundary_floor` (the `end_time` guard at `:653`),
  the fold and marking at `:1835-1867`, the cell suffixes at `:354-355`, the two provenance constants at
  `:340`/`:348`, and the two co-rendering annotations at `:2066-2097`.
- **Checks run:**
  - Collection: `TestUnclosedBoundaryFold` = **7** tests, `TestOverCoveringBoundaryIsNotCalledAFloor` =
    **5**. Both counts re-derived by collection; both match the report.
  - **Mutation:** `if phase_row.get('end_time'): return None` deleted →
    `test_a_closed_phase_takes_no_floor_marker` **FAILS**
    (`assert 'unclosed_boundary_floor' == 'dispatch_boundary_total'`).
  - **Mutation:** `if _boundary_coverage_state(phase) == 'over':` → `if False:` → 3 over-covering tests
    **FAIL**. Reverse mutation → `if True:` → 4 tests **FAIL**, including the `partial`-coverage
    negative control. The discrimination fires in both directions.
  - **Mutation:** `if current is None or floor > current:` → `if True:` →
    `test_the_fold_never_lowers_a_cell` **FAILS**.
  - Duration partiality: `phases_missing_end_time` (`:1563-1565`) keys off `end_time` alone and the fold
    does not touch it; `test_the_duration_partiality_verdict_survives_the_fold` fails under the
    over-covering mutation, so it is anchored to the fold rather than to an empty fixture.
- **Verdict:** CONFIRMED. One judgement call examined and found defensible: an **undecidable**-coverage
  sum (no `subagent_samples`) is labelled `(boundary floor)`. Because the declared exclusions guarantee
  under-coverage of dispatched spend, and because both the boundary file and `total_tokens` accumulate
  across closes, the lower-bound claim survives the re-entry case; the `over` state is an
  incommensurability signal rather than evidence of inflation, which is exactly how R4-F7 already
  re-worded its annotation.

### D6 — two derived figures whose names assert the wrong population

- **Required (plan):** (arm 1) a per-task duration derived from wall clock must read the recorded worked
  figure — **not** clamping, **not** gap heuristics; (arm 2) the persistence loop must derive its usage
  field list from the canonical label set.
- **Claimed (report):** arm 1 renamed and re-sourced with 3 tests over an 8-hour idle gap including a
  clamp positive control; arm 2 derives from `_FOUR_FIELD_USAGE_LABELS` with a source-level guard.
- **Found:**
  - Arm 1: `plan-retrospective/references/plan-efficiency.md:88` (fragment shape), `:110` (the rule),
    `:112` (⛔ no clamping / no gap heuristics), `:114` (unclosed-boundary corollary), `:129`/`:131`
    (threshold, declared unanchored), `:71-72` (explicit `/ 1000`, the F1 fix, with `worked_seconds`
    correctly named the NUMERATOR — the F10 fix). Fixture updated at
    `test/plan-marshall/plan-retrospective/fixtures/archived-plan/work/fragment-plan-efficiency.toon:12`.
  - Arm 2: `manage-metrics.py:381` `_FOUR_FIELD_USAGE_FIELDS = tuple(field for field, _label in
    _FOUR_FIELD_USAGE_LABELS)` and its single consumer at `:3504` `for field in
    _FOUR_FIELD_USAGE_FIELDS:`; guard at
    `test/plan-marshall/manage-metrics/test_persisted_aggregate_round_trip.py:601-610`.
  - Substrate tests: `TestWorkedTimeExcludesTheIdleGap` (3 tests, `:304-402`), driving a real 8-hour
    wall span against a 10-minute worked span, with a positive control that pushes a
    worked-exceeds-wall row through `end-phase` and observes it clamped (`:365-379`).
- **Checks run:** collection of the three tests; reading `_worked_ms` (`:1364`) and `_wall_clock_ms`
  (`:1334`); grep for every in-tree consumer of `seconds_per_task` / `worked_seconds_per_task`.
- **Verdict:** PARTIAL. Arm 2 is CONFIRMED in code. Arm 1's change is entirely a change to an LLM-read
  reference contract; the shipped tests verify the substrate and say so themselves
  (`"the ratio itself has no script to test"`, `:307-309`), and **nothing asserts the emitted key
  name** — the F14 fix updated the fixture without adding an assertion, so a regression to
  `seconds_per_task` would still pass silently. The report's D6 verification cell presents the three
  substrate tests without that distinction. See G8 and G10.

### D7 — tests, each verified to FAIL pre-fix

- **Required (plan):** (a) divergent rows → a finding per row; (b) population-mismatched comparison
  refused or annotated; (c) a total rendered without a population marker fails the assertion.
- **Found / checks run:** each driven red by a targeted mutation in this audit —
  (a) window widened → `test_the_window_is_a_real_bound_in_both_directions` fails;
  `test_one_finding_per_divergent_row_not_one_per_phase` exists at
  `test_ledger_reconciliation.py:175`;
  (b) refusal gate disabled → two refusal tests fail;
  (c) population counts withheld from the store write → four tests fail, including the one the
  deliverable names.
- **Verdict:** CONFIRMED.

## Correctness review

Read in full: `_ledger_reconciliation.py` (all 482 lines); `manage-metrics.py` §§ population constants
(`:225-404`), coverage/reconciliation helpers (`:515-660`), `write_metrics` / `read_metrics_raw`
(`:900-1030`), `cmd_generate`'s completion, fold, aggregate and render (`:1556-2100`),
`cmd_reconcile_ledgers` (`:2964-3035`), `cmd_enrich`'s persistence and stamping (`:3489-3597`), and the
`reconcile-ledgers` parser (`:3735-3764`); `check-routing-decisions.py:430-718`.

Defects found:

1. **A refuted claim ships in `--help` text.**
   `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:3744-3745` —
   `'boundary_never_closed (the rows exist, the phase aggregate is missing) versus row_absent_from_*'`.
   Round 2 (R2-F3) established that wording is false: `_reconcile_accumulator_into_phase` backfills
   `total_tokens` from the durable accumulator and the D5 fold supplies the Tokens cell, so an unclosed
   phase's aggregate is frequently **present**. The corrected wording is used everywhere else —
   `_ledger_reconciliation.py:443-446` (`'the rows are present and no close recorded the phase's own
   summary of them'`) and `SKILL.md:616`. A whole-tree grep for the refuted phrasing returns exactly
   this one production site. → **G1**.

2. **`RecursionError` reaches the caller as a traceback.** Reproduced: with 999 execution rows and 999
   boundary rows sharing one timestamp, `pair_rows` raises
   `RecursionError: maximum recursion depth exceeded` (500 → ok, 900 → ok, 999 → raise, 1 200 → raise,
   default limit 1 000). The module's own stated rule is that unusable input degrades to a reported
   state rather than taking the process down (`_parse_iso.__doc__`, `:100-113`); this path does not.
   Carried in the report as survivor R4-F4. → **G3**.

3. **A boolean is summed as a count.** `check-routing-decisions.py:496` —
   `if isinstance(value, int): total += value`. `True` is an `int`, so a `total_tokens: true` row adds 1.
   The sibling module explicitly refuses this: `_ledger_reconciliation.py:145-147`,
   `"""Coerce a TOON scalar to int … Booleans are not counts."""`. Unreachable from the current writers,
   but the two readers of the same column disagree about the same input. → **G6**.

No other defect was found. Specifically checked and found sound: the fold's raise-only rule and its
interaction with the reconciliation winner (`:1835-1860`); the `_total_str` empty-subset and
`k < breakdown_n` branches (`:1956-1971`); `write_metrics`'s scoping of the drop to the row-derived
family with `dispatch_boundary_excluded_classes` deliberately retained (`:948-957`); the
`predicted is None` / `recorded_unparseable` three-state split and the `predicted == 0` guard on
`delta_pct` (`check-routing-decisions.py:656-717`); `cmd_reconcile_ledgers`' empty-block suppression
(`:2998`, `:3011-3016`) against the `not_evaluated` path; the finalize step order
(`end-phase` → `enrich` → `generate`, `record-metrics.md:35`) and `cmd_phase_boundary`'s trailing
`cmd_generate` (`:2820`), which together mean the persisted aggregate genuinely survives into the
archived record; and that `cmd_enrich` stamps `total_tokens_population` on **all three** branches
(`:3584`, `:3586`, `:3593`, `:3595`), which is the precondition the `generate` completion loop relies on.

## Test adequacy

Baseline: `pytest test_ledger_reconciliation.py test_persisted_aggregate_round_trip.py
test_check_routing_decisions.py test_plan_retrospective_manifest.py -o addopts=""` → **141 passed**.

| Deliverable | Covering tests | Mutation evidence |
|---|---|---|
| D2 | `TestExecutionLogPopulation` (2), `TestExecutionLogSumMatchesItsPublishedPopulation` (2), `TestRoutingDecisionsAspect` cost-preview (11) | Refusal gate → `if False:` ⇒ 2 refusal tests red |
| D3 | `TestPersistedAggregate` (9), `TestInlineCostFieldOnEveryRow` (3) | Invalidation → `if False:` ⇒ red; count → `breakdown_n` ⇒ 8 red; population counts withheld from the file write ⇒ 4 red |
| D4 | `TestManifestParsing`, `TestDivergentRowsProduceFindings` (5), `TestTheTwoPartialityShapes` (4), `TestDeclaredAndUndecidableStates` (4), `TestPairingIsMaximal` (4), `TestMixedTimezoneAwarenessDoesNotCrash` (3) + 1 module-level drift test | Window → `10**9` ⇒ 2 red; sort key neutralised ⇒ 2 red. **Maximality mutation SURVIVES** |
| D5 | `TestUnclosedBoundaryFold` (7), `TestOverCoveringBoundaryIsNotCalledAFloor` (5) | `end_time` guard removed ⇒ red; `over` discrimination in both directions ⇒ 3 and 4 red; never-lowers rule ⇒ red |
| D6 | `TestWorkedTimeExcludesTheIdleGap` (3, substrate only), `test_four_field_persistence_walks_the_canonical_label_set` (source-level) | Not mutated — arm 1 has no production code to mutate; arm 2's guard is a source-text assertion |

Two adequacy gaps, both proven rather than suspected:

- **`pair_rows`' maximality is unpinned.** Replacing the augmenting recursion with plain first-fit
  (`if holder is None or _augment(holder, visited):` → `if holder is None:`) leaves **all 22 tests
  green**. `test_a_nearer_partner_is_given_up_when_another_row_needs_it` names *nearest-first* greedy,
  which the implementation never was — it iterates candidates in index order, and on that corpus
  index-order first-fit already pairs both rows. The 3 000-corpus brute force the report cites was an
  out-of-tree exercise; nothing in the suite would catch a regression. → **G2**.
- **The `worked_seconds_per_task` key name is unasserted.** The only in-tree occurrences outside
  `plan-efficiency.md` are the fixture (`fragment-plan-efficiency.toon:12`) and a comment in
  `test_persisted_aggregate_round_trip.py:307`. No assertion reads the key, so F14's remediation
  ("nothing asserts the key name") changed the fixture without closing the hole it named. → **G8**.

## Report accuracy

Re-derived at the moment of writing, and true of the tree now:

- Build gate "**9 Python files**" — `git show --stat 85abeeb` lists exactly 9 `.py` paths. ✓
- Findings table "**58 rows**" — counted programmatically from the table: **58**. ✓ Round split
  21 / 13 / 7 / 14 ✓ and self-caught 1 + 2 = 3 ✓ (total 55 + 3 = 58 ✓).
- Cost figures — 279 458 + 278 356 + 214 719 + 225 251 = **997 784** ≈ "998 K" ✓;
  1 142 + 2 813 + 852 + 1 503 = 6 310 s = **1 h 45 min** ✓; 07:38:45 → 10:57:53 = **3 h 19 min** ✓.
- D2's "11 behavioural + 2 contract-drift + 2 population-filter" ✓ (collection).
- D5's "12 tests (7 fold + 5 over-covering)" ✓ (collection).
- D6 arm 1's "3 tests over a real 8-hour idle gap" ✓ (collection; the 8 h / 10 min constants are at
  `test_persisted_aggregate_round_trip.py:317-319`).
- Every D1 code citation lands on the claimed symbol ✓ (line numbers differ, as the report warns).
- The writer list "`start-phase`, `end-phase`, `phase-boundary`, `enrich`" ✓ — the five `write_metrics`
  call sites resolve to exactly those four plus `cmd_generate`.
- "`TOKEN_POPULATIONS` … this plan consumes it and defines no new member" ✓ — untouched in the diff.
- "`reconcile-ledgers` has no caller … zero workflow call sites" ✓ — still true.
- Report-01's "12 commits" and status-report's "13, including this one" are **consistent**, not
  contradictory: the status report's own commit is the thirteenth.

Claims that are stale, imprecise, or overstated:

1. **D4's "19 tests".** `pytest test_ledger_reconciliation.py --collect-only` reports **22**. The three
   extra are the `TestMixedTimezoneAwarenessDoesNotCrash` tests the R4-F5 row separately claims, so the
   two rows are reconcilable — but the report also states, as R4-F10's remediation, that "every count in
   this report re-derived by collection at the final commit", and 19 is not what collection of the named
   module returns. → **G5**.
2. **The findings table is 58 rows but 57 instances.** The un-numbered "round 2" row about commit
   `82ee8ad`'s message and the `R2-F10` row describe the same instance and cross-reference each other,
   against the table's own stated rule "One row per instance". → **G9**.
3. **D6's verification cell overstates arm 1.** It reads "Arm 1: 3 tests over a real 8-hour idle gap …"
   in a column headed *Verification state*, while the tests' own class docstring says the ratio "has no
   script to test" and verifies the substrate instead. Nothing verifies that the emitted fragment
   carries the renamed key or the new numerator. → **G10**.
4. **F18's bound, "D4's stated *Done when* is met — the verb exists, is documented and is tested",** is
   literally true but sits beside a Goal ("a cross-ledger disagreement produces a finding instead of a
   silent choice") that no run can reach. The report says as much in its own Residue section; the
   deliverable table does not. → **G4** (the work item), not a separate report defect.

Every other factual claim in `report-01.md` that this audit could reach held. `status-report.md`'s
claims about CI state, PR number, reviewer verdicts and the merge gate are **UNVERIFIABLE** here — the
head SHAs it names are not objects in this clone and no network check was performed — but its central
claim is corroborated: the plan did land, as squash commit `85abeeb`.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| The verification loop stopped on its budget, not convergence; more claim-family instances likely, "most densely in this report" | **Yes — and one is in production, not only in the report** | `manage-metrics.py:3744-3745` restates R2-F3's refuted claim in the shipped `--help` description (G1). The report's own prediction was right about the *rate*, wrong about the *location* |
| "At least one further test in the new modules probably asserts a property it cannot fail on" | **Yes — confirmed by mutation** | The maximality mutation leaves all 22 `test_ledger_reconciliation.py` tests green (G2) |
| "Any figure not re-derived at the moment of writing is stale" | **Yes — one instance** | D4's "19 tests" against a module that collects 22 (G5) |
| **F18** — `reconcile-ledgers` has no caller | **Yes, unchanged** | Whole-tree grep: definition, parser, `SKILL.md`, tests, executor registry. Zero workflow call sites (G4) |
| **F19** — the D3/D5 guards' pre-fix failure is a module-level collection error | **Moot** | Superseded by direct evidence: this audit mutation-tested those guards individually and each went red. The bound's stated remedy has no behavioural gain |
| **R2-F10** — a pushed commit message states 17 findings where it closes 18 | **Moot** | The PR was squash-merged as `85abeeb`; the individual commit messages are not in this clone's history and the count no longer exists anywhere but the report |
| **R4-F4** — `_augment` recursion cliff at N≈999 | **Yes — reproduced** | 999 same-timestamp rows on both sides ⇒ `RecursionError: maximum recursion depth exceeded`; 900 ⇒ ok (G3). Its containment by F18 also still holds |
| **R4-F2 residue** — which unpaired row a finding names | **Yes, and correctly characterised** | `pair_rows.__doc__:277-286` states the limit outright; not a defect to fix |
| **The `worked_seconds_per_task > 900` threshold is unanchored** | **Yes, and disclosed** | `plan-efficiency.md:131` declares it unanchored and refuses an invented conversion factor. Correctly left open |
| Contract-amendment proposal (report's "What have we learned") recorded, not shipped | **Yes, open** | Grep of `.claude/skills/cloud-plan-lane/SKILL.md` was not performed as part of this deliverable's scope; the proposal is by construction an orchestrator collect-step item |

## Out-of-scope and collateral

The plan excluded four things. None was built:

- **Structurally-empty per-dispatch context-load columns** — the diff touches no `_CONTEXT_COLUMNS` /
  `unmeasured_context_load_columns` logic; the only `*_main_context_*` hunks are
  `inline_main_context_tokens`, which is D3's explicit scope.
- **Defining the population vocabulary** — `TOKEN_POPULATIONS` is untouched by the diff.
- **The render-path recovery of a lost report section** — no such change in the 18 changed files.
- **Per-call cost truncation at the runtime and hook layer** — no runtime or hook file in the diff.

Collateral declared and reasonable: `phase-6-finalize/standards/record-metrics.md` gained a one-sentence
correction (`enrich` leaves a cache-read-only phase to `generate`'s measured `0`), which is a direct
consequence of D3's completion loop and is accurate against `manage-metrics.py:1595-1610`.

One unstated deviation worth recording: the run coined `POPULATION_UNSTATED = 'unstated'` and the
comma-joined phase-list convention (`EXECUTION_LOG_POPULATION`) in `check-routing-decisions.py`. The
report considered and rejected the objection with a reason, and the reasoning holds — these live on a
**different axis** from `TOKEN_POPULATIONS` (which population a token figure measures vs which phase set
a sum covers). But no document says so, so a consumer reading `total_tokens_population: dispatched`
beside `execution_log_population: 5-execute,6-finalize` has no in-tree statement that the two are not
comparable. → **G7**.

## Method and coverage

- Read `plan.md`, `report-01.md` and `status-report.md` in full, then the whole of
  `_ledger_reconciliation.py`, `check-routing-decisions.py:430-718`, and the sections of
  `manage-metrics.py` named in the Correctness review, plus `SKILL.md`, `data-format.md`,
  `plan-efficiency.md`, `routing-decision-verification.md` and `record-metrics.md`.
- Ran the four affected test modules (141 passed) and performed **11 targeted mutations**, each via a
  snapshot-mutate-run-restore harness that writes the original bytes to
  `$SCRATCH/verify-340-mutsweep/` and restores from that snapshot. `git checkout` / `git restore` /
  `git stash` were never used. `git status --porcelain` was verified clean for both mutated files after
  the sweep (`marketplace/bundles/plan-marshall/skills/manage-metrics/` and
  `.../plan-retrospective/` report no modifications).
- Wrote two out-of-tree probes under the scratchpad: a 5 000-corpus comparison of `pair_rows` against a
  first-fit greedy, and a recursion-depth probe. Neither touched the repository.
- Re-derived every count stated here at the moment of stating it (collection runs, programmatic row
  counts, arithmetic on the report's own operands). No number was copied from the run report and
  presented as a measurement.
- Negative-control discipline: before treating any "grep found nothing" as evidence, the same pattern
  was confirmed to hit where it was known to exist (e.g. the refuted "aggregate is missing" wording hits
  `manage-metrics.py:3745` and the report's own rows, so the empty result elsewhere is meaningful).

**Not checked, and why:**

- **The three ledgers' arithmetic.** `.plan/local/plans/` does not exist in this clone, so the
  "twice / three / four in the union" figures remain UNVERIFIABLE — the same blockage the run reported,
  independently confirmed rather than assumed.
- **CI, PR and reviewer state.** `f1b9eb9`, `cf1ba0b`, `4dcc65b` and the other branch SHAs are not
  objects here; no network call was made. Every claim in `status-report.md` about check conclusions,
  reviewer bodies and merge-gate conditions is UNVERIFIABLE from this tree.
- **`./pw verify`.** Deliberately not run (out of scope per the audit brief); the four affected test
  modules were run instead.
- **Whether the contract-amendment proposal was carried to the orchestrator.** Outside this plan's
  artifacts.
