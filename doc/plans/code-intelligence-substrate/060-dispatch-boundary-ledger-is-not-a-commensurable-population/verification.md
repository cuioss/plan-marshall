# Verification — 060-dispatch-boundary-ledger-is-not-a-commensurable-population

**Audited:** `plan.md`, `report-01.md`
**Tree state:** `61a43e5` on `claude/code-intelligence-substrate-analysis-kah884`; every finding
re-derived in an independent adversarial pass against the same `manage-metrics.py` bytes
(md5 `b9c88ef9c59542e53a483498aaac4b03`, matching `git show HEAD:`) — see § Adversarial review.
**Landed as:** `3f64b71 fix(manage-metrics): dispatch-boundary ledger is a declared, commensurable population (#1173)`
**Overall verdict:** CONFIRMED WITH GAPS

The plan landed. All five deliverables are present in the tree, the fail-first claim is
independently reproducible from git history, and the out-of-scope boundaries were respected. Two
correctness gaps remain in the shipped behaviour: the D2 failure verdict cannot fire on a whole
class of rows, and D4's agreement clause is emitted only in the one population where its claim is
unsound, and never in the same-population case the deliverable was written for.

## Deliverable verdicts

| # | Deliverable (short) | Report claim | Ground truth | Verdict |
|---|---|---|---|---|
| D1 | GATE: declare the population; class count and registering count as two source-derived figures | 9 classes exist, 3 register; fork REFUTED | Independently re-derived from `call-graph.md` + every `record-dispatch-boundary` invocation block: 3 register (4-plan, 5-execute, 6-finalize). The "9" folds the change-type-heuristic LLM fallback into `phase-3-outline`, and `report-01.md:43` declares that fold in the class table; the fold is not carried onto the shipped surfaces | CONFIRMED |
| D2 | An impossible ratio is a loud failure naming both populations; never `complete`; no clamping | `_boundary_coverage_state` + `over` → `FAILURE`, refused the maximum | Implemented at `manage-metrics.py:525-562`, `:600`, `:2204-2215`. But the whole bullet is gated on a truthy `dispatch_boundary_total` (`:2183`), so an over-covering row whose boundary sum is `0` renders **no verdict at all** | PARTIAL |
| D3 | Every class registers, or the non-registering classes appear in an explicit exclusion list the coverage figure references | `DISPATCH_BOUNDARY_EXCLUDED_CLASSES`, 6 classes, rendered as a declaration | Constant at `:515-522`, rendered at `:2112-2122`, persisted at `:1941`. The list is a hand-maintained literal with no guard tying it to the call sites, is missing the change-type fallback, and the coverage figure does not reference it (the reference runs the other way) | PARTIAL |
| D4 | Equal figures annotated as agreement; a test pins smaller/equal/larger | `_reconciliation_relation_clause` renders the true relation | Implemented at `:661-683`. But the `equal` branch is unreachable for a same-population row (the tie resolves to `total_tokens`, which suppresses the annotation entirely), and the only rows that reach the clause at all are `inline`-population rows, where all three relations compare across populations | PARTIAL |
| D5 | Three tests, each verified to FAIL pre-fix; characterization arm labelled | 8 tests; 7 failed / 1 passed pre-fix | 8 tests present and passing (`test_dispatch_boundary_ledger_population.py`, 299 lines). Fail-first reproduced independently against `3f64b71^`. The characterization arm is labelled. The D3 negative control the plan specified was not performed | CONFIRMED WITH GAPS |

## Per-deliverable detail

### D1 — GATE: declare the population

- **Required (plan):** "the class count and the registering count are reported as **two separate
  figures**, both derived from source"; the class list derived from the dispatching code, never
  from a run.
- **Claimed (report):** 9 dispatch classes exist; 3 register; 6 do not. Source of truth named as
  `ref-workflow-architecture/standards/call-graph.md` cross-checked against `record-dispatch-boundary`
  call sites. The fork (omission → impossible ratio) declared **REFUTED**.
- **Found:** The two figures are stated as separate figures in `report-01.md:57-58` and restated in
  code at `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:512-514`
  and in shipped docs at
  `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:348-350`.
- **Checks run:**
  - Independent enumeration from `call-graph.md`: five phase envelopes (`:67-72`) plus four shared
    workflows — `verification-feedback`, `q-gate-validation`, `research`, `enrich-module` (`:341-384`).
    `phase-1-init` runs inline and is correctly excluded (`:395`).
  - Independent registration sweep: the marketplace holds **four** executable
    `record-dispatch-boundary` invocation blocks, resolving to **three** registering phases —
    `plan-marshall/workflow/planning-outline.md:463` (`--phase 4-plan`),
    `plan-marshall/workflow/execution.md:212` (`--phase 5-execute`, the ordinary post-dispatch
    call), `plan-marshall/workflow/execution.md:257` (`--phase 5-execute` again — the *synthesized*
    clean-exit row written on the pre-dispatch queue peek, with a literal
    `--total-tokens 0 --tool-uses 0 --duration-ms 0`), and
    `phase-6-finalize/SKILL.md:1109` (`--phase 6-finalize`, per dispatched step, item 5c).
    The registering-phase count of 3 is unaffected — both execution.md blocks write the same
    phase — but the fourth block is load-bearing for G1, because it prescribes an all-zero
    boundary row.
    Positive control: the same grep pattern returns those four hits, so a zero result elsewhere is
    a real absence, not a filtered search.
  - The asserted **absences** were each confirmed by reading: no `record-dispatch-boundary` appears
    in the q-gate-validation, verification-feedback, research, or enrich-module workflow surfaces.
- **Verdict:** CONFIRMED — the derivation method is correct, both figures are reported separately
  and from source, and the registering count of 3 is exact.
  One folding decision sits behind the class count of 9: `call-graph.md:154-158` draws the
  change-type-heuristic LLM fallback as its own orchestrator-side `execution-context` dispatch with
  no role key, and `planning-outline.md:273-275` names it as a separate dispatch whose `<usage>` must
  be summed. The report **does** declare the fold — its class table row 2 reads "phase-3-outline
  (main envelope, + change-type LLM fallback)" (`report-01.md:43`) — so D1's own *Done when* is met.
  What the fold does not survive is the crossing onto the shipped surfaces: neither
  `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` nor `data-format.md:346-350` records it, so a reader of the
  shipped total cannot reconstruct which dispatches the "9" folds. That is a D3 disclosure gap, not
  a D1 derivation failure. See G6 (re-severitied low).
  The fork refutation is sound: the omission drives `rows < samples` (under-coverage) while the
  reported symptom is `rows > samples`, and `cmd_record_dispatch_boundary` appends across re-entries
  (`:3194-3198`) while `subagent_samples` is a single enrich-window figure (`:3513`) — an
  accumulate-vs-window asymmetry that produces over-coverage independently.

### D2 — a recorded-vs-expected ratio is commensurable, or it does not render

- **Required (plan):** "an impossible ratio produces a failure verdict, and the populations behind
  both figures are named in the output"; no clamping.
- **Claimed (report):** new `_boundary_coverage_state` classifier (undecidable / partial / exact /
  over); the `over` case renders a loud `FAILURE` naming both producers and is refused the
  reconciliation maximum, "not just the display".
- **Found:**
  - Classifier: `manage-metrics.py:525-562`.
  - Ineligibility (not a display fix): `:600` — `if field == 'dispatch_boundary_total' and
    boundary_state in ('partial', 'over'): continue`.
  - `FAILURE` render naming both producers: `:2204-2215`.
- **Checks run:**
  - Ran the shipped suite: `test/plan-marshall/manage-metrics/` → **456 passed** (28s).
  - Mutation probe (against a copy in `$TMPDIR`, never the repo file): deleting the `over` branch
    from `_boundary_coverage_state` makes the D5(a) assertion fail — the test is not vacuous.
  - **Defect probe.** Rendered a phase with `dispatch_boundary_rows_recorded: 8`,
    `subagent_samples: 3` and no `dispatch_boundary_total`. Output contained **no
    `Dispatch-boundary total` bullet at all** and no `FAILURE`. Root cause: `:1445` persists
    `dispatch_boundary_total` only when the sum is non-zero, while `:1439-1444` deliberately
    persists `dispatch_boundary_rows_recorded` even when the rows sum to zero — and the render at
    `:2183` gates on the total, not on the coverage state. All-zero boundary rows are not merely
    reachable, they are **prescribed**: the legacy `total_tokens` column defaults to `0` (`:3157`),
    the workflow docs instruct callers to pass `0` when the field is absent
    (`planning-outline.md:468`, `execution.md:219`), and `execution.md:254-260` requires the
    orchestrator to *synthesize* a boundary row with a literal
    `--total-tokens 0 --tool-uses 0 --duration-ms 0` whenever the pre-dispatch queue peek finds the
    queue already drained ("the peek itself is the clean signal — there is no agent return to parse,
    so token / tool-use / duration counters are recorded as `0`").
- **Verdict:** PARTIAL — the classifier and the ineligibility rule are correct and the failure text
  names both populations. The verdict cannot fire on rows whose boundary sum is zero, which is
  precisely the row the code's own comment at `:1440-1443` says the row count exists to make
  legible. No clamping was introduced. See G1.

### D3 — every dispatch records a boundary, or the ledger names the classes it excludes

- **Required (plan):** "either every enumerated class registers, or the non-registering classes
  appear in an explicit exclusion list **that the coverage figure references**."
- **Claimed (report):** `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` constant (source-derived, 6 classes)
  "rendered as a declaration the coverage figures reference"; verified by the exclusion test, a
  source-derivation guard, and a negative control.
- **Found:** constant `manage-metrics.py:515-522`; render `:2112-2122`; persisted to the store as
  `dispatch_boundary_excluded_classes` at `:1941` and documented at `data-format.md:518`.
- **Checks run:**
  - Mutation probe: forcing `boundary_surface_present` false makes the D5(b) assertion fail — the
    render guard is under test.
  - Read the render: the declaration block appears under the **Phase Breakdown** table; the coverage
    figures live in **Phase Details** (`:2199-2220`) and contain no pointer to it. The reference runs
    declaration → coverage ("A phase whose boundary rows fall short of its subagent_samples is short
    by exactly these excluded classes"), not coverage → declaration as the plan worded it.
  - Searched the whole test tree for any structural-equality guard tying the constant to
    `call-graph.md` or to the `record-dispatch-boundary` call sites: **none exists**. The only
    guards are `test_exclusion_constant_is_source_derived_not_a_registering_phase`
    (`test_dispatch_boundary_ledger_population.py:183-193`), which asserts membership for 2 of the 6
    and non-membership for the 3 registering phases, and the round-trip assertion at
    `test_persisted_aggregate_round_trip.py:219`. Both compare the constant to itself or to a
    hard-coded literal. The repository's own convention for exactly this hazard is stated at
    `manage-metrics/SKILL.md:446` — "When adding a new full-set enumeration, either derive it from
    the tuple or add a structural-equality test, and prefer deriving" — and is implemented for
    `DISPATCH_TERMINATION_CAUSES` by the contract test at
    `test/plan-marshall/manage-metrics/test_manage_metrics.py:3871-3876`, which discovers every
    enumeration site in the shipped doc and compares it to the tuple. (`data-format.md:944`,
    "Restating surfaces (lock-step obligation)", states the same obligation for the boundary-row
    *column schema*, a different enumeration — it is the convention's sibling, not its statement
    for this constant.) It was not applied here.
- **Verdict:** PARTIAL — the exclusion list ships, renders, and persists. It is a hand-maintained
  literal that claims source-derivation with nothing enforcing it, it omits the change-type fallback,
  and the reference direction the plan specified is inverted. See G4, G6, G9.

### D4 — the comparator stops mislabelling exact agreement

- **Required (plan):** "equal figures are annotated as agreement, and a test pins the three-way
  distinction (smaller / equal / larger)." The plan's ⭐ note: an exact agreement between two
  independent producers is "the single most valuable signal this surface can emit."
- **Claimed (report):** `_reconciliation_relation_clause` renders the true `>` / `=` / `<` relation;
  exact agreement reads as agreement.
- **Found:** `manage-metrics.py:661-683`. The three-way clause is correct in isolation and the
  annotation site is `:2014-2026`.
- **Checks run:**
  - Mutation probe: deleting the `value == beaten` branch makes the D5(c) equal test fail — the
    branch is under test.
  - **Reachability analysis, then probe.** The clause is only emitted for phases in
    `reconciled_phases`, and a phase enters that list only when the winning field is **not**
    `total_tokens` (`:1798`). `_reconcile_dispatched_measures` resolves ties to the earliest declared
    field (`:606-615` over `_DISPATCHED_MEASURE_FIELDS = (total_tokens, dispatch_boundary_total,
    subagent_total_tokens)`), so whenever `total_tokens` is eligible and ties the maximum it wins and
    the annotation is suppressed.
  - Probe against a pristine `HEAD` copy: a row with `total_tokens: 5000`,
    `subagent_total_tokens: 5000`, `dispatch_boundary_total: 5000`, `rows: 2`, `samples: 2` — three
    independent producers in exact agreement — rendered **no reconciliation line at all**. The
    identity the deliverable calls the most valuable signal is silent.
  - The only way to reach the `equal` branch is for `total_tokens` to be *ineligible*, which happens
    only on an `inline`-population row (`:593`). The shipped test
    (`test_dispatch_boundary_ledger_population.py:237-260`) does exactly that: it sets
    `total_tokens_population = POPULATION_INLINE`. On such a row `beaten` is still the raw
    `total_tokens` (`:1793`, `:1800-1801`) — a **main-context** figure — so "measures agree" is
    asserted between two populations the same module declares non-comparable at `:483-486` and
    `data-format.md:306-310`.
  - **The cross-population problem is not confined to the `equal` branch.** An `inline` row is the
    only row that reaches the clause at all, so `>` and `<` are computed against the same
    main-context `beaten`. Probe against a pristine `HEAD` copy, `total_tokens: 5000` stamped
    `inline` with `subagent_total_tokens: 3000`, rendered
    `> Tokens reconciled across the competing measures of the dispatched population … 4-plan →
    subagent_total_tokens 3,000 (< total_tokens 5,000)` — while the population annotation lower in
    the same report says the phase dispatched nothing and the cell is the main-context-window
    measurement. The annotation's own preamble calls `total_tokens` a competing measure of the
    dispatched population on a row the render simultaneously declares inline. The `<` branch is the
    shipped test's own scenario (`:262-278`), so this is the *common* path, not a corner.
  - Reachable on real data, not only in fixtures: `enrich` writes `subagent_total_tokens` /
    `subagent_samples` first (`:3509-3513`), then stamps `total_tokens_population = inline` on any
    row whose `total_tokens` is falsy at that moment (`:3579-3584`). A dispatching phase that never
    closed with `--total-tokens` therefore carries dispatched measures *and* an `inline` stamp.
  - The gate itself is documented, so this is a design gap rather than a code/doc mismatch:
    `data-format.md:325-332` states the annotation renders "When the winner is NOT `total_tokens`".
- **Verdict:** PARTIAL — the wording defect the plan named is fixed and the three-way test exists.
  The agreement signal is unreachable in the same-population case, and every relation the clause
  does emit is a cross-population comparison. See G2, G3.

### D5 — tests, each verified to FAIL pre-fix

- **Required (plan):** three named tests, each verified to fail against unmodified code before the
  fix; a test that passes today must be labelled a characterization test.
- **Claimed (report):** 8 tests in
  `test/plan-marshall/manage-metrics/test_dispatch_boundary_ledger_population.py`; fail-first
  "7 failed, 1 passed" pre-fix, "8 passed" after.
- **Found:** the file exists (299 lines) with exactly **8** test functions, re-counted at audit time.
  The characterization arm is explicitly labelled in the module docstring (`:26-29`) and in
  `test_larger_dispatched_winner_annotated_as_above_total` (`:280-284`).
- **Checks run:**
  - `uv run python -m pytest test/plan-marshall/manage-metrics/ -o addopts=""` → 456 passed.
  - **Fail-first independently reproduced.** Extracted `3f64b71^`'s `manage-metrics.py` to
    `$TMPDIR` and rendered the same three scenarios against it:
    - D5(a): `- **Dispatch-boundary total**: 900,000 (dispatched-subagent population; **8 of 3
      dispatch(es) recorded — complete**; won the reconciliation maximum)` — the plan's OBSERVED-but-
      unreachable artifact reproduced exactly, and worse than claimed: the impossible measure also
      *won* the maximum.
    - D5(b): no `excluded by declaration` string anywhere in the pre-fix render.
    - D5(c): `4-plan → subagent_total_tokens 5,000 (> total_tokens 5,000)` for equal figures.
    - Characterization arm: `(> total_tokens 439,628)` — passed pre-fix, as declared.
  - Vacuity sweep by mutation on copies (never the repo file): three mutations, three red — the
    `over` classification, the `equal` clause, and the exclusion render are each genuinely pinned.
- **Verdict:** CONFIRMED WITH GAPS — the tests exist, are non-vacuous, and the fail-first claim is
  true. The plan's § Verification also required a specific D3 negative control ("remove a class's
  registration and confirm it appears in the list rather than silently shrinking the denominator").
  The test bearing that name (`:195-220`) does not remove any registration; it seeds a shortfall row
  and asserts the static constant renders. Because the constant is a hand-maintained literal, the
  control as specified would *refute* the implementation. See G5.

## Correctness review

Read in full: `manage-metrics.py:279-360` (population/coverage constants), `:433-683` (the whole
reconciliation and coverage block), `:727-810` (boundary-file reader), `:900-1028` (store read/write
and numeric coercion), `:1420-1479` (boundary persistence), `:1690-2260` (the entire `generate`
render path), `:3101-3200` (the boundary writer), `:3495-3524` (enrich's `subagent_samples` write).
Two defects and one dead symbol found; both defects reproduced by execution against a pristine
`HEAD` copy, and re-reproduced independently in the adversarial pass.

1. **`manage-metrics.py:2183` — the coverage verdict is gated on the wrong field.** The
   `Dispatch-boundary total` bullet, which carries every coverage verdict including the `over`
   `FAILURE`, renders only `if boundary_total:`. `dispatch_boundary_total` is persisted only when
   non-zero (`:1445`), whereas `dispatch_boundary_rows_recorded` is persisted whenever the file held
   rows (`:1439-1444`). Failing input: any phase whose boundary rows all carry `total_tokens: 0`
   (the documented default) and whose `subagent_samples` is lower than the row count. Consequence:
   the impossible ratio is silent — the exact fail-open D2 exists to close. This also falsifies the
   shipped claim at `data-format.md:333-334` that the bullet "states the measure's coverage on every
   render".

2. **`manage-metrics.py:615` + `:1798` + `:1793` — the agreement identity is unreachable where it
   matters and unsound where it is reachable.** `max()` over `_DISPATCHED_MEASURE_FIELDS` resolves a
   tie to `total_tokens`, and a `total_tokens` winner is never added to `reconciled_phases`, so a
   same-population three-way exact agreement produces no annotation. The `equal` branch is therefore
   reachable only when `total_tokens` was ruled ineligible as cross-population — and `beaten` is
   that same cross-population figure, so "measures agree" is asserted across two populations the
   module elsewhere refuses to compare.

No fail-open branch, unguarded `None`, or off-by-one was found in `_boundary_coverage_state` itself:
both counts are `isinstance`-guarded (`:552-557`), `read_metrics_raw` coerces phase-row values to
`int` on read (`:1014-1021`) so the guards fire on real data, and the three-way comparison is
exhaustive. The `over` measure is genuinely refused the maximum (`:600`), not merely re-labelled.

## Test adequacy

| Deliverable | Covering test(s) | Non-vacuity evidence |
|---|---|---|
| D2 | `test_over_coverage_renders_failure_naming_both_populations`, `test_over_covering_measure_is_ineligible_for_the_maximum` | Mutation M1 (delete the `over` branch of `_boundary_coverage_state`) → assertion fails |
| D3 | `test_excluded_classes_are_named_in_the_report`, `test_exclusion_constant_is_source_derived_not_a_registering_phase`, `test_negative_control_dispatched_phase_shortfall_is_declared_not_silent` | Mutation M3 (suppress the `boundary_surface_present` block) → assertion fails |
| D4 | `test_equal_boundary_and_total_annotated_as_agreement`, `test_smaller_dispatched_winner_annotated_as_below_total`, `test_larger_dispatched_winner_annotated_as_above_total` (characterization) | Mutation M2 (delete the `equal` branch) → assertion fails |

All mutations were applied to copies under `$TMPDIR/verify-060-mutsweep/`; the repository file was
never written. `md5sum` of `manage-metrics.py` matches `git show HEAD:` and `git status --porcelain`
lists no modification to it.

Weaknesses, none vacuous but each under-powered:

- `test_exclusion_constant_is_source_derived_not_a_registering_phase` is named for a derivation it
  does not check. It asserts 2 of the 6 excluded names and the absence of the 3 registering ones —
  all against the same hand-written literal it is guarding. Nothing reads the call graph or the
  workflow docs, so the constant can drift silently from the dispatching code it claims to mirror.
- `test_negative_control_dispatched_phase_shortfall_is_declared_not_silent` asserts
  `'q-gate-validation' in report`, which is true for *any* report carrying a boundary surface
  because the declaration is unconditional. The assertion cannot distinguish a phase-specific
  shortfall from the global banner.
- No test covers the zero-sum over-coverage row (G1).
- No test covers a same-population exact agreement (G2).

## Report accuracy

Every substantive claim in `report-01.md` was checked. Findings:

- **True.** "8 tests in `test/plan-marshall/manage-metrics/test_dispatch_boundary_ledger_population.py`"
  — re-counted: 8 test functions.
- **True.** "Fail-first confirmed: 7 failed, 1 passed against unmodified code (the 1 passing is the
  declared `larger` characterization arm)" — independently reproduced against `3f64b71^`; the
  characterization arm passes and the three regression scenarios fail, with the pre-fix render
  literally emitting `8 of 3 dispatch(es) recorded — complete`.
- **True.** "Dispatch classes that exist: 9 / register a boundary: 3" as to the *registering* count;
  the class count omits the change-type-heuristic LLM fallback dispatch (G6).
- **True.** "The fork … REFUTED" — the direction argument holds and the accumulate-vs-window
  mechanism is visible in the code.
- **True.** "no `record-dispatch-boundary` call added, no display clamping" — the landed diff
  (`git show --stat 3f64b71`) touches only `manage-metrics.py`, `standards/data-format.md`, the new
  test, and the plan documents.
- **Stale, low.** The D1 evidence column cites `workflow/planning-outline.md:468`,
  `workflow/execution.md:216`, and `phase-6-finalize/SKILL.md:1051`. The current lines are `463`,
  `212`, and `1109`. The call sites are still there; the line anchors have drifted.
- **Superseded, not false.** "No regression in the 398-test manage-metrics suite" — the suite now
  holds **456** tests (re-measured), all passing. The growth is from later plans.
- **UNVERIFIABLE.** "`./pw verify` (full): 19052 passed, 14 skipped" and the per-commit
  quality-gate logs. The brief forbids running the full verify suite, and the branch commits
  (`02d098a`, `2312559`, `952c4e5`, `b1d85f5`, `344cb43`) were squashed at merge and are absent from
  this shallow clone. The single merged commit `3f64b71` exists and its contents match the report's
  description.
- **UNVERIFIABLE.** The reviewer-participation table and the "1 of 3" coverage figure — PR-comment
  state is not readable from the clone.
- **Overstated by inheritance (shipped doc, not the report).** `data-format.md:333-334` — "The
  `Dispatch-boundary total` bullet states the measure's coverage **on every render**". False for a
  zero-sum boundary file; see G7.

## Declared residue — current status

| Residue item (from report) | Still open? | Evidence |
|---|---|---|
| **Landing** — auto-merge armed on PR #1173, `state: MERGED` delegated | **Closed** | `3f64b71 fix(manage-metrics): dispatch-boundary ledger is a declared, commensurable population (#1173)` is in `main`'s history, and its content is present in the tree |
| **Review coverage** — 1-of-3 by reviewer rate limits | **Moot** | A per-run disclosure with no owed action; the PR is merged |
| **Contract amendment** — add `clean` to the `mergeStateStatus` enumeration in the merge gate, pending operator decision | **Closed** | Shipped as `3a5e2ca chore(cloud-plan-lane): document the clean mergeStateStatus in the merge gate (#1177)`; the text now reads at `.claude/skills/cloud-plan-lane/SKILL.md:1344-1345` — "**`clean`** means every required context has passed … **`UNSTABLE` and `clean` both report the required contexts satisfied**" |

## Out-of-scope and collateral

All four exclusions were respected, verified against the landed diff:

- **The retrospective's render path** — `marketplace/bundles/plan-marshall/skills/plan-retrospective/`
  is untouched by `3f64b71`.
- **The step/dispatch emission arm** — no `record-dispatch-boundary` call site was added; the three
  call sites in the tree are the same three that existed pre-fix.
- **Clamping or smoothing** — no clamp exists; the over-covering figure is refused eligibility
  (`:600`) rather than being adjusted, and it is rendered with its true value plus a `FAILURE`
  annotation.
- **Re-deriving per-phase cost rankings** — no ranking code was added.

No collateral change was found. The `TOKENS_SOURCE_UNCLOSED_BOUNDARY_OVER` fold at `:1845-1860` and
the `manage-metrics/SKILL.md` exclusion prose at `:596-597` / `:721` are **not** this plan's work —
they were added later (the SKILL.md text by `85abeeb (#1293)`), and they consume this plan's
classifier correctly.

## Method and coverage

- **Read:** the epic README, `plan.md`, `report-01.md`; `manage-metrics.py` (the whole
  reconciliation, persistence, render, and writer blocks); `standards/data-format.md`;
  `ref-workflow-architecture/standards/call-graph.md`; the three `record-dispatch-boundary` call
  sites; the D5 test file in full; the neighbouring metrics test files for guard coverage.
- **Ran:** the full `test/plan-marshall/manage-metrics/` suite (456 passed); five audit probes and
  three mutation probes, each loading a **copy** of the production module from
  `$TMPDIR/verify-060-mutsweep/` so the repository file was never written; a pre-fix reconstruction
  from `git show 3f64b71^:…` to reproduce the fail-first evidence.
- **Counts re-derived at audit time:** 8 tests in the D5 file; 456 tests in the metrics suite; 3
  `record-dispatch-boundary` call sites; 6 names in `DISPATCH_BOUNDARY_EXCLUDED_CLASSES`; 5 phase
  envelopes + 4 shared workflows in the call graph.
- **False-negative control:** before treating any "not found" as an absence, the same pattern was
  confirmed to hit where the target is known to exist (`record-dispatch-boundary` returns the three
  call sites; `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` returns the constant, the render, the persist
  site and the tests).
- **Concurrency hazard, disclosed.** Sibling audit agents were mutating the same working tree during
  this audit; at one point `manage-metrics.py` carried a foreign `# MUTATED-050` edit at line 1426.
  Every finding reported here was re-confirmed against a pristine `git show HEAD:` copy after that
  was observed, and the file's `md5sum` was checked to match `HEAD` at the end of the audit.
- **Could not check:** the full `./pw verify` totals (out of scope per the brief); the branch-local
  commit SHAs and per-commit quality-gate logs (squashed away, shallow clone); PR review and CI
  states (not readable from the clone); the machine-local `.plan/` run record that originally
  exhibited the impossible ratio — the plan explicitly forbids hunting for it, and the capability
  was instead confirmed by executing the pre-fix renderer.
