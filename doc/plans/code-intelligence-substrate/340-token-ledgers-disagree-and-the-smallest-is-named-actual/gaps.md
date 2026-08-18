# Gaps — 340-token-ledgers-disagree-and-the-smallest-is-named-actual

The plan's seven deliverables all shipped and the five load-bearing guards (population-mismatch refusal,
aggregate invalidation, population-count persistence, the unclosed-boundary `end_time` guard, the
over-covering marker) were each driven red by mutation, so the core is sound. What remains is ten
instances in three families: one refuted claim that survived into shipped `--help` text; two unpinned or
unreachable behaviours in the new reconciliation verb (a maximum matching no test can distinguish from
greedy, and a recursion cliff carried by the machinery that produces it); the verb having no caller, so
the plan's Goal is reached in principle only; and four smaller report/doc/test defects. No gap is
`high` — nothing shipped mis-measures, and no guard was found unable to fire.

## G1 — Correct the `reconcile-ledgers` `--help` description, which restates a claim round 2 refuted

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:3744-3745`
  (the `description=` argument of the `reconcile-ledgers` subparser)
- **Evidence:** the shipped text reads
  `'distinctly: boundary_never_closed (the rows exist, the phase '` /
  `'aggregate is missing) versus row_absent_from_* (a specific row has '`.
  Finding R2-F3 in `report-01.md` records that exact claim as false and "fixed at all three" sites;
  R3-F4 found a fourth. The corrected wording is used everywhere else —
  `_ledger_reconciliation.py:443-446` emits
  `"the rows are present and no close recorded the phase's own summary of them, which is not the same
  defect as an absent row"`, and `manage-metrics/SKILL.md:616` says the same. A whole-tree grep for
  `aggregate is missing` (excluding `doc/plans/` and `__pycache__`) returns this one production site.
- **Why it matters:** an unclosed phase's aggregate is frequently **present** —
  `_reconcile_accumulator_into_phase` backfills `total_tokens` from the durable accumulator, and this
  plan's own D5 fold supplies the Tokens cell. A reader of `--help` is told the opposite of what the
  verb's own emitted `detail` string says, and `--help` output is captured into the generated executor's
  surface cache, so it is a first-class documentation surface rather than a comment.
- **Action:** replace the parenthetical with the wording already used in `_phase_findings` — e.g.
  `boundary_never_closed (the rows are present; no close recorded the phase's own summary of them)`.
- **Done when:** `grep -rn "aggregate is missing" marketplace/` returns nothing, and the subparser
  description and `_ledger_reconciliation.py`'s `detail` string state the same fact.
- **Effort:** S
- **Risk if fixed:** none beyond a `plugin-doctor` help-cache regeneration; no behaviour changes.

## G2 — Pin `pair_rows`' maximality with a test that a greedy implementation fails

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py:328-340`
  (`_augment`, the Kuhn's-algorithm augmenting path) and
  `test/plan-marshall/manage-metrics/test_ledger_reconciliation.py:418-507` (`TestPairingIsMaximal`)
- **Evidence:** mutating `if holder is None or _augment(holder, visited):` to `if holder is None:` —
  which reduces the matching to plain first-fit greedy — leaves **all 22 tests in the module green**
  (`22 passed in 0.48s`). `test_a_nearer_partner_is_given_up_when_another_row_needs_it` names
  *nearest-first* greedy, which the implementation never was: it iterates `candidates[...]` in index
  (i.e. timestamp) order, and on that corpus index-order first-fit already pairs both rows. A 5 000-corpus
  probe (0–6 rows per side, windows 60/300/600 s) found the two algorithms produce equal-size matchings
  in **5 000/5 000** cases — the eligibility sets are contiguous index intervals with monotone endpoints,
  so no hand-written corpus will separate them.
- **Why it matters:** R3-F6 introduced maximum matching precisely because a non-maximal pairing
  "manufactures spurious findings — a false signal about the ledgers, manufactured by the verb built to
  surface them". That property is currently defended by nothing: any future simplification of `_augment`
  (including the one G3 invites) would land green.
- **Action:** add a property test that generates random corpora and asserts `len(pair_rows(...)[0])`
  equals a brute-force maximum matching computed in the test (exhaustive enumeration is fine at ≤6 rows
  per side). That test fails against any genuinely non-maximal implementation, which a fixed corpus
  cannot. Optionally record in `pair_rows.__doc__` that first-fit is provably equivalent on this
  eligibility structure, so the next reader knows why the fixed-corpus test cannot bite.
- **Done when:** reverting `_augment` to `if holder is None:` makes at least one test in
  `test_ledger_reconciliation.py` fail.
- **Effort:** M
- **Risk if fixed:** a randomised test can be flaky if seeded from the clock — seed it deterministically.

## G3 — Remove the `_augment` recursion cliff by replacing the recursion with its equivalent iteration

- **Kind:** bug
- **Severity:** low (contained today by G4 — nothing invokes the verb; it becomes medium the moment a
  workflow does)
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py:328-340`
- **Evidence:** reproduced in this audit. With N execution rows and N boundary rows sharing one
  timestamp: N=500 → ok, N=900 → ok, **N=999 → `RecursionError: maximum recursion depth exceeded`**,
  N=1 200 → same (default `sys.getrecursionlimit()` is 1 000). The exception propagates out of
  `cmd_reconcile_ledgers` as a traceback, not as a TOON error block — while the module's own stated rule
  (`_parse_iso.__doc__`, `:100-113`) is that an input it cannot use "degrades to a reported state rather
  than taking the process down". Carried in `report-01.md` as survivor R4-F4.
- **Why it matters:** a phase that recorded ~1 000 dispatches is the exact phase whose ledgers most need
  reconciling, and it is the one shape where the verb dies instead of reporting.
- **Action:** replace `_augment`'s recursion with an explicit stack, or — given G2's finding that
  first-fit in the module's own sort order is maximum for this eligibility structure — with the plain
  iterative first-fit, keeping G2's property test as the guarantee. Either way, add a regression test at
  N ≈ 1 200 same-timestamp rows per side.
- **Done when:** `pair_rows` over 1 200 identical-timestamp rows on both sides returns a result instead
  of raising, and a test asserts it.
- **Effort:** M
- **Risk if fixed:** an iterative rewrite could change *which* row is reported unpaired among equally
  pairable rows — already documented as immaterial in `pair_rows.__doc__:277-286`, and the per-phase
  counts (the figures consumers are told to read) are unaffected.

## G4 — Wire `reconcile-ledgers` into a workflow so a cross-ledger disagreement actually surfaces

- **Kind:** omission
- **Severity:** medium
- **Topic:** dispatch/finalize
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:2964`
  (`cmd_reconcile_ledgers`); the natural call site is `phase-6-finalize/standards/record-metrics.md`
  after the `end-phase` → `enrich` → `generate` sequence
- **Evidence:** whole-tree grep for `reconcile-ledgers`, excluding `doc/plans/` and `__pycache__`,
  returns `manage-metrics/SKILL.md` ×3 (docs), `manage-metrics.py` ×3 (usage banner, subparser,
  `set_defaults`), `test_ledger_reconciliation.py:68`, and the generated executor's surface registry.
  **Zero workflow call sites** — unchanged since the report recorded it as survivor F18.
- **Why it matters:** the plan's Goal is "a cross-ledger disagreement produces a finding instead of a
  silent choice". D4's literal *Done when* is met, but no run invokes the verb, so on every real plan the
  disagreement is still silent. The report's own Residue says wiring a call site "is the natural next
  plan".
- **Action:** add the invocation to the finalize metrics step (read-only, after `generate`, and — like
  the other three — never blocking archive), log its `findings_count` and `union_rows` as a work-log
  line, and surface a `[WARN]` when `findings_count > 0`. Decide explicitly whether the findings feed
  `manage-findings` or stay a work-log observation; that decision is the scoping the previous run
  declined to make.
- **Done when:** a plan run's work log carries a `reconcile-ledgers` line naming `union_rows` and
  `findings_count`, and a test drives the finalize step over a disagreeing corpus and observes the line.
- **Effort:** M
- **Risk if fixed:** a noisy new `[WARN]` on every plan if the declared-exclusion suppression is
  incomplete; and G3's recursion cliff stops being contained, so fix G3 first or in the same change.

## G5 — Re-derive D4's test count in `report-01.md`, or scope it to the shapes it covers

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/340-token-ledgers-disagree-and-the-smallest-is-named-actual/report-01.md:127`
  (the D4 row's Verification-state cell)
- **Evidence:** the row says "19 tests, each shape with a negative control".
  `pytest test/plan-marshall/manage-metrics/test_ledger_reconciliation.py --collect-only -q` reports
  **22 tests collected**. The three extra are `TestMixedTimezoneAwarenessDoesNotCrash`, which the R4-F5
  row claims separately — so the two rows are reconcilable, but R4-F10's stated remediation is "every
  count in this report re-derived by collection at the final commit", and 19 is not what collection of
  the named module returns.
- **Why it matters:** the report is the artifact a later plan reads to decide what is already covered; a
  count that no command reproduces is exactly the defect family the run spent four rounds on.
- **Action:** change the cell to "22 tests in `test_ledger_reconciliation.py` (19 for D4's shapes, 3 for
  the reviewer's zone-naive fix)", or restate it as 22.
- **Done when:** the number in the D4 row equals the module's collection count, or the cell names the
  subset it counts.
- **Effort:** S
- **Risk if fixed:** none.

## G6 — Refuse booleans in `sum_execution_log_tokens`, as the sibling reader already does

- **Kind:** bug
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py:495-499`
- **Evidence:**
  ```python
  value = row.get('total_tokens')
  if isinstance(value, int):
      total += value
  ```
  `True` is an `int` in Python, so a row carrying `total_tokens: true` contributes 1 to a token sum. The
  sibling reader of the same column refuses it explicitly:
  `_ledger_reconciliation.py:145-147` — `"""Coerce a TOON scalar to int, defaulting to 0. Booleans are
  not counts."""` with `if isinstance(value, bool): return 0`.
- **Why it matters:** two readers of one column disagree about the same input, and the disagreeing one is
  the sum published under a population label. Unreachable from the current writers, but the whole point
  of the D2 filter (R4-F13) was that the label must be a property of the sum, not a promise about
  another process.
- **Action:** add `if isinstance(value, bool): continue` before the `int` test, or reuse the same
  coercion shape as `_as_int`.
- **Done when:** `sum_execution_log_tokens({'execution_log': [{'phase': '5-execute',
  'total_tokens': True}]}) == 0`, asserted by a test.
- **Effort:** S
- **Risk if fixed:** none — no real writer emits a boolean there.

## G7 — State that the two `*_population` field families measure different axes

- **Kind:** doc-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:15-31`
  (the Token-Field Population Lattice) and
  `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/routing-decision-verification.md:64-82`
- **Evidence:** `total_tokens_population` takes values from `TOKEN_POPULATIONS`
  (`dispatched` / `inline` / `mixed`, `manage-metrics.py:237`) and names *how* a figure was measured.
  `execution_log_population` / `predicted_population` take comma-joined phase lists plus the coined
  `POPULATION_UNSTATED = 'unstated'` (`check-routing-decisions.py:454`, `:463`) and name *which phase set*
  a sum covers. Neither document mentions the other; grep for `execution_log_population` in
  `manage-metrics/standards/data-format.md` returns nothing.
- **Why it matters:** the plan's keeper rule is that a figure carries its population. A consumer reading
  `total_tokens_population: dispatched` beside `execution_log_population: 5-execute,6-finalize` has no
  in-tree statement that these are orthogonal and that neither answers the other's question — which is
  the same "two vocabularies, one word" hazard the plan was written to remove.
- **Action:** add one paragraph to the lattice's **Populations** section naming the phase-set axis as a
  distinct, separately-owned family, with a cross-reference to
  `routing-decision-verification.md` § "The cost-preview comparison is population-gated"; and add the
  reciprocal pointer there.
- **Done when:** both documents cross-reference each other and state that a measurement-method population
  and a phase-set population are not comparable.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Assert the `worked_seconds_per_task` key name, which F14's fix left unpinned

- **Kind:** test-gap
- **Severity:** low
- **Topic:** tests
- **Where:** `test/plan-marshall/plan-retrospective/fixtures/archived-plan/work/fragment-plan-efficiency.toon:12`
  and `test/plan-marshall/plan-retrospective/test_registered_aspects_render.py`
- **Evidence:** finding F14 reads "fixture … still carried `seconds_per_task`, **passing silently because
  nothing asserts the key name** | fixed — fixture carries `worked_seconds` and
  `worked_seconds_per_task`". The fixture was changed; no assertion was added.
  `grep -rn "worked_seconds_per_task" test/` returns only the fixture line and a comment at
  `test_persisted_aggregate_round_trip.py:307`. The same silence that let the old key survive is intact.
- **Why it matters:** D6 arm 1 IS the rename plus the numerator change, and it lives entirely in an
  LLM-read contract (`plan-efficiency.md`). Reverting the contract to `seconds_per_task` over
  `duration_seconds` would leave the suite green.
- **Action:** assert in the aspect-render test that the fragment's `ratios:` block carries
  `worked_seconds_per_task` and not `seconds_per_task`, and that `totals:` carries `worked_seconds`.
  Optionally add a source-level guard over `plan-efficiency.md` mirroring the one already used for the
  `enrich` loop (`test_persisted_aggregate_round_trip.py:601-610`).
- **Done when:** renaming the key back to `seconds_per_task` in
  `references/plan-efficiency.md` or in the fixture makes a test fail.
- **Effort:** S
- **Risk if fixed:** a source-text assertion over a prose file is brittle to rewording — key on the
  identifier only.

## G9 — Collapse the duplicated finding row so the table's stated count equals its instance count

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/340-token-ledgers-disagree-and-the-smallest-is-named-actual/report-01.md:162`
  (the un-numbered "round 2" row) and `:180` (`R2-F10`)
- **Evidence:** both rows say commit `82ee8ad`'s message states "Seventeen findings" where it closes 18,
  and each cross-references the other ("row above"). Programmatic count of the table gives **58 rows**;
  distinct instances are **57**. The table's own preamble states "One row per instance".
- **Why it matters:** the report's headline finding count is the number a retrospective reads, and the
  table declares a rule it breaks once.
- **Action:** delete the un-numbered duplicate (keeping `R2-F10`, which the survivors table already
  references) and restate the header count as 57 with the round split adjusted, or add one sentence
  explaining the deliberate duplication.
- **Done when:** the stated row count equals the number of distinct instances, or the exception is
  declared in the preamble.
- **Effort:** S
- **Risk if fixed:** none.

## G10 — Scope D6's verification cell to what the three tests actually verify

- **Kind:** report-defect
- **Severity:** low
- **Topic:** documentation-surface
- **Where:** `doc/plans/code-intelligence-substrate/340-token-ledgers-disagree-and-the-smallest-is-named-actual/report-01.md:129`
  (the D6 row's Verification-state cell)
- **Evidence:** the cell reads "Arm 1: 3 tests over a real 8-hour idle gap, including a positive control
  that drives a worked-exceeds-wall row through `end-phase` …". Those tests exist
  (`test_persisted_aggregate_round_trip.py:304-402`) and are non-vacuous, but their own class docstring
  states the limit: *"`plan-efficiency`'s `worked_seconds_per_task` is computed by an LLM from a
  reference contract, so the ratio itself has no script to test. What IS script-level … is that the
  figure the contract tells it to read — `totals_worked_ms` — reflects worked time"* (`:307-311`). The
  rename and the numerator change themselves are unverified by any executable check (see G8).
- **Why it matters:** the Verification-state column is what a later plan reads to decide a deliverable is
  covered. Here it names three tests for a change they verify only the substrate of, and the report's
  Residue section does not carry the shortfall.
- **Action:** reword the cell to "Arm 1: substrate verified by 3 tests over a real 8-hour idle gap (the
  worked/wall split the contract reads); the LLM-produced ratio itself has no script-level check — see
  the test class docstring", and add the shortfall to the Residue list.
- **Done when:** the D6 cell distinguishes the substrate check from the ratio change, and the Residue
  section names the unverified half.
- **Effort:** S
- **Risk if fixed:** none.
