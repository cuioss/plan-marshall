# Gaps — 340-token-ledgers-disagree-and-the-smallest-is-named-actual

The plan's seven deliverables all shipped and the five load-bearing guards (population-mismatch refusal,
aggregate invalidation, population-count persistence, the unclosed-boundary `end_time` guard, the
over-covering marker) were each driven red by mutation, so the core is sound. What remains is **ten
instances in five families**:

- **One false claim in shipped documentation** — the `reconcile-ledgers` `--help` description restates a
  claim round 2 refuted (G1).
- **One contained bug in the new verb, and one unrecorded fact that makes its fix cheaper** — a recursion
  cliff (G3) in an augmenting path that is provably redundant, which nothing says (G2). Fix them
  together.
- **One omission** — the verb has no caller, so the plan's Goal is reached in principle only (G4).
- **Two missing-test / cross-reader-inconsistency items** — the `worked_seconds_per_task` key name is
  unasserted (G8) and one of two readers of `total_tokens` sums booleans as counts (G6).
- **Four documentation-surface defects** — three in `report-01.md` (G5, G9, G10) and one missing
  cross-reference between the two `*_population` field families (G7).

No gap is `high` — nothing shipped mis-measures, and no guard was found unable to fire.

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

## G2 — Record that `_augment` is provably redundant, so G3 can delete it rather than rewrite it

- **Kind:** doc-defect *(re-kinded from `test-gap`, and substantially re-based, by adversarial review —
  the original entry's two central claims were refuted; see "What the first audit got wrong" below)*
- **Severity:** low *(lowered from `medium`)* — the calibration's "a harmless unstated deviation".
  Nothing mis-measures: the shipped pairing **is** a maximum matching. The property the module was fixed
  for **is** pinned by a non-vacuous test. What is unrecorded is that the machinery achieving it is
  redundant, and the only cost of that silence is that G3's fix looks riskier than it is.
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py:249-286`
  (`pair_rows.__doc__`) and `:322-340` (the Kuhn's comment and `_augment`)
- **Evidence:**
  - Mutating `if holder is None or _augment(holder, visited):` (`:334`) to `if holder is None:` — plain
    first-fit over the same candidate lists — leaves **all 22 tests in the module green** and **all 456
    tests in `test/plan-marshall/manage-metrics/` green**.
  - Re-derived over **21 056 corpora** in four out-of-tree probes: 5 000 random (0–6 rows per side,
    windows 60/300/600 s); 7 056 **exhaustive** over a six-value offset alphabet at ≤3 rows per side;
    3 000 dense-tie corpora clustered on the window boundary; 6 000 including unparseable timestamps on
    both sides. In **every** corpus the two forms produced a matching of the same size, both equal to a
    brute-force maximum — and, beyond the size, **the identical set of unpaired rows**. Since the unpaired
    rows are what become findings, nothing observable through this module separates them.
  - The structural reason: `pair_rows` sorts both sides internally by `_row_sort_key` (`:301-302`), which
    sorts unparseable stamps last, so each execution row's eligible boundary indices form a **contiguous
    interval** whose endpoints are **non-decreasing** as the execution row's timestamp increases. That is
    a convex bipartite graph traversed in non-decreasing right-endpoint order, for which taking the
    smallest free eligible index is already a maximum matching. The equivalence is therefore a property
    of the input shape this module guarantees itself, not of the corpora that were sampled.
- **⚠ What the first audit got wrong** (recorded because a later run would otherwise re-derive it):
  - It wrote that `test_a_nearer_partner_is_given_up_when_another_row_needs_it` "names *nearest-first*
    greedy, **which the implementation never was**". `report-01.md:188` (R3-F6) states the opposite in the
    run's own record: "`pair_rows` **was** nearest-first greedy" until round 3 replaced it.
  - It concluded that maximality "is currently defended by nothing". It is defended. Restoring the exact
    R3-F6 defect — sorting each `eligible` list by absolute timestamp gap **and** dropping the augmenting
    path, which is nearest-first greedy — drives
    `test_a_nearer_partner_is_given_up_when_another_row_needs_it` **red** (`1 failed, 21 passed`). The
    test is non-vacuous against the defect it names. What it does not distinguish is *index-order*
    first-fit — a different algorithm, and one that provably cannot regress anything.
  - Its *Done when* ("reverting `_augment` to `if holder is None:` makes at least one test fail") is
    **unsatisfiable**, and its proposed remedy (a randomised property test asserting the matching size
    equals a brute-force maximum) passes against both forms, so it could not have delivered that
    *Done when*. Both are superseded by the entry below.
- **Why it matters:** `_augment` carries G3's recursion cliff and buys no behaviour. Nothing in the
  module says so, so the obvious reading of G3 is "make the recursion iterative", which preserves
  machinery that has no reason to exist. One recorded sentence turns G3 into a deletion.
- **Action:** add to `pair_rows.__doc__`, beside the existing ⛔ paragraph (which stays — it correctly
  records why nearest-first greedy was replaced), a note stating that on this eligibility structure —
  contiguous intervals with monotone endpoints, guaranteed by the internal sort at `:301-302` — first-fit
  in the module's own candidate order is *already* maximum, so the augmenting path changes no output and
  may be replaced by plain first-fit. Name the property that must hold for that to stay true (the
  internal sort), so a future change that breaks it is visibly breaking a stated precondition.
- **Done when:** `pair_rows.__doc__` states the first-fit equivalence and names the internal sort as its
  precondition, and G3's fix cites that note as its justification for deleting rather than rewriting
  `_augment`.
- **Effort:** S; do it inside G3's change.
- **Risk if fixed:** none to behaviour. The note must not weaken the existing statement that the RESULT is
  a maximum matching — that remains true and is what the verb publishes.

## G3 — Remove the `_augment` recursion cliff by replacing the recursion with its equivalent iteration

- **Kind:** bug
- **Severity:** low (contained today by G4 — nothing invokes the verb; it becomes medium the moment a
  workflow does)
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/_ledger_reconciliation.py:328-340`
- **Evidence:** reproduced twice — in the first audit and independently in adversarial review. With N
  execution rows and N boundary rows sharing one timestamp: N=500 → ok, N=900 → ok, **N=999 →
  `RecursionError: maximum recursion depth exceeded`**, N=1 200 → same (default
  `sys.getrecursionlimit()` is 1 000). The exception propagates out of `cmd_reconcile_ledgers` as a
  traceback, not as a TOON error block — while the module's own stated rule (`_parse_iso.__doc__`,
  `:100-113`) is that an input it cannot use "degrades to a reported state rather than taking the process
  down". Carried in `report-01.md` as survivor R4-F4.
- **Why it matters:** a phase that recorded ~1 000 dispatches is the exact phase whose ledgers most need
  reconciling, and it is the one shape where the verb dies instead of reporting. G2 sharpens this: the
  recursion is the **only** cost the augmenting path carries, because it changes no output.
- **Action:** replace `_augment` with the plain iterative first-fit — take the first free eligible index
  in candidate order. G2 establishes that this is not an approximation but an exact equivalence on every
  input this module can produce (21 056 corpora, identical matchings *and* identical unpaired sets), so
  the rewrite is behaviour-preserving rather than a trade. ⛔ **Do not plan to defend it with a test that
  distinguishes the two implementations** — G2 shows none exists. What the change needs instead is the
  equivalence note G2 asks for, in `pair_rows.__doc__`, stating the precondition (the internal sort) that
  makes first-fit maximum here. Add a regression test at N ≈ 1 200 same-timestamp rows per side, which
  pins the thing that *is* observable: that the call returns rather than raising.
- **Done when:** `pair_rows` over 1 200 identical-timestamp rows on both sides returns a result instead
  of raising, and a test asserts it.
- **Effort:** M
- **Risk if fixed:** lower than the first audit recorded. It reasoned that an iterative rewrite "could
  change *which* row is reported unpaired among equally pairable rows"; the adversarial probe measured
  that it does not — across 21 056 corpora the first-fit form left **the same rows** unpaired as the
  augmenting form, never merely the same number. Even had it differed, the variation is documented as
  immaterial in `pair_rows.__doc__:277-286` and the per-phase counts consumers are told to read are
  exact either way.

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
- **Topic:** bundle-docs *(re-topiced from `documentation-surface` by adversarial review: this gap edits
  two in-bundle documents, the same surface family as G1. `documentation-surface` is carrying the three
  `report-01.md` defects (G5, G9, G10), and grouping a bundle-standards change with them would route it
  into a report-correction plan that never opens `marketplace/`.)*
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
- **Done when:** `grep -n execution_log_population marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md`
  and `grep -n total_tokens_population marketplace/bundles/plan-marshall/skills/plan-retrospective/references/routing-decision-verification.md`
  each return at least one line (both return nothing today), and each hit sits in a sentence stating that
  a measurement-method population and a phase-set population are not comparable.
- **Effort:** S
- **Risk if fixed:** none.

## G8 — Assert the `worked_seconds_per_task` key name, which F14's fix left unpinned

- **Kind:** test-gap
- **Severity:** medium *(raised from `low` by adversarial review: this is the calibration's "a vacuous or
  missing test on a load-bearing path" applied to the load-bearing half of a deliverable the audit itself
  could only mark **PARTIAL**. D6 arm 1 IS the rename plus the numerator change; nothing executable
  covers either, so the deliverable rests on an unverified edit to an LLM-read contract. It is not any of
  the `low` cases — it is neither confined to the run report, nor cosmetic, nor a harmless deviation.
  G10, which is the separate defect of the **report** overstating this coverage, correctly stays `low`.)*
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
