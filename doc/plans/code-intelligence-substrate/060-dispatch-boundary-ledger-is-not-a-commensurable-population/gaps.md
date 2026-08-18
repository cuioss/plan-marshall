# Gaps — 060-dispatch-boundary-ledger-is-not-a-commensurable-population

The plan landed and its four behavioural deliverables are present, but three of them are incomplete
in ways that leave the original defect reachable. The D2 failure verdict is gated on the wrong field
and cannot fire for a boundary file whose rows sum to zero — the one row shape the code's own
comments say the row count exists to make legible. D4's agreement signal is unreachable for a
same-population exact agreement (the tie resolves to `total_tokens`, which suppresses the annotation
entirely) and is emitted only in a cross-population comparison where "measures agree" is unsound.
D3's exclusion list is a hand-maintained literal that claims source-derivation with no guard
enforcing it, omits one dispatch class, and is not referenced by the coverage figure as the plan
required. Nine gaps follow.

## G1 — Gate the boundary coverage verdict on the coverage state, not on a truthy boundary sum

- **Kind:** bug
- **Severity:** high
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:2182-2229`
  (`cmd_generate`, the `Dispatch-boundary total` bullet), with the persistence asymmetry at `:1439-1446`
- **Evidence:** The bullet — which carries every coverage verdict, including the `over` `FAILURE`
  that D2 exists to emit — is guarded by `boundary_total = phase.get('dispatch_boundary_total')` /
  `if boundary_total:`. But `:1445` persists `dispatch_boundary_total` only `if boundary_sum:`, while
  `:1439-1444` persists `dispatch_boundary_rows_recorded` whenever the file held rows, with the
  comment "The row count persists whenever the file held rows, INCLUDING the case where they sum to
  zero: the sum alone cannot state its own coverage, and a measure that cannot state its coverage is
  the one this field exists to make legible." Rendering a phase with
  `{'dispatch_boundary_rows_recorded': 8, 'subagent_samples': 3, 'total_tokens': 100000}` produced a
  report containing **no `Dispatch-boundary total` bullet and no `FAILURE`** — only the generic
  declaration banner. (Reproduced twice, independently, against a pristine copy of the shipped
  module.) All-zero boundary rows are not a contrived shape — they are **prescribed by the workflow
  contract**: `cmd_record_dispatch_boundary` defaults the `total_tokens` column to `0` (`:3157`);
  `plan-marshall/workflow/planning-outline.md:468` and `plan-marshall/workflow/execution.md:219`
  both instruct callers to "use `0` when the field is absent"; and
  `plan-marshall/workflow/execution.md:254-260` requires the orchestrator to *synthesize* a boundary
  row with a literal `--total-tokens 0 --tool-uses 0 --duration-ms 0` on the pre-dispatch queue peek
  ("the peek itself is the clean signal — there is no agent return to parse, so token / tool-use /
  duration counters are recorded as `0`"). A phase whose boundary file holds only such rows sums to
  `0` while `dispatch_boundary_rows_recorded` counts them all.
- **Why it matters:** an over-covering ledger — the impossible ratio this plan was written to make
  loud — renders completely silently on any phase whose boundary rows carry no token measurement.
  The reader sees a phase with no boundary bullet at all, which is indistinguishable from a phase
  that recorded no boundary. That is D2 failing open on exactly the population D3 declared.
- **Action:** change the render guard so the coverage verdict is emitted whenever the coverage state
  is decidable, independently of the sum. Concretely: compute `boundary_state =
  _boundary_coverage_state(phase)` first and render the bullet when
  `boundary_state is not None or boundary_total` — showing the sum as `0` where that is the measured
  value. Consider also persisting `dispatch_boundary_total` unconditionally when
  `dispatch_boundary_rows_recorded` is persisted, so the two fields never disagree about whether the
  file existed.
- **Done when:** a `generate` over a phase row carrying `dispatch_boundary_rows_recorded: 8`,
  `subagent_samples: 3` and no non-zero `dispatch_boundary_total` renders a `FAILURE` coverage
  verdict naming both producers, and a regression test in
  `test/plan-marshall/manage-metrics/test_dispatch_boundary_ledger_population.py` pins it.
- **Effort:** S
- **Risk if fixed:** a bullet now renders on rows that previously showed none, so any test or
  downstream reader that asserted on the absence of the `Dispatch-boundary total` line for a
  zero-sum phase will need updating. `_unclosed_boundary_floor` (`:618-658`) already guards on a
  non-zero sum and is unaffected.

## G2 — Emit the agreement identity for a same-population exact agreement

- **Kind:** incomplete
- **Severity:** medium
  (Re-severitied from high on adversarial review. The defect is real and reproduced, but it is an
  *unemitted* signal, not a wrong one: nothing false is rendered, the Tokens cell is correct, and
  D4's literal *Done when* — "equal figures are annotated as agreement, and a test pins the
  three-way distinction" — is satisfied, if only on the unsound row G3 covers. Under the
  calibration that is "an incomplete deliverable" (medium), while the *misreport* half of the same
  defect is G3, now high. Fix G2 and G3 together; G2's fix is what makes G3's test honest.)
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:606-615`
  (`_reconcile_dispatched_measures` tie resolution) and `:1794-1805` (`reconciled_phases` gate)
- **Evidence:** `max(eligible, key=lambda item: item[1])` returns the first maximal element and
  `_DISPATCHED_MEASURE_FIELDS` is ordered `(total_tokens, dispatch_boundary_total,
  subagent_total_tokens)`, so an exact tie always resolves to `total_tokens`. `:1798` then appends to
  `reconciled_phases` only `if winning_field != 'total_tokens'`, and the annotation at `:2014-2026`
  only renders for phases in that list. Probe: rendering
  `{'total_tokens': 5000, 'subagent_total_tokens': 5000, 'dispatch_boundary_total': 5000,
  'dispatch_boundary_rows_recorded': 2, 'subagent_samples': 2}` — three independent producers in
  exact agreement, coverage `exact` — produced **no `Tokens reconciled across…` line at all**
  (the row's only annotation was the boundary bullet's `2 of 2 dispatch(es) recorded — complete`,
  which states row-count agreement, never token agreement). Reproduced independently on adversarial
  review against a pristine copy of the shipped module.
- **Why it matters:** `plan.md` D4 calls exact agreement between two independent producers "the
  single most valuable signal this surface can emit — it is the reconciliation identity the
  attribution work proved by arithmetic." In shipped code that signal is emitted for no
  same-population row. The deliverable fixed the mislabel but did not deliver the signal.
- **Action:** decouple the annotation from "the winner is not `total_tokens`". Record the phase
  whenever two or more eligible measures were compared and state the relation among them — including
  the all-equal case — so a three-way agreement renders as an explicit agreement line.
- **Done when:** a `generate` over a row whose `total_tokens`, `dispatch_boundary_total` and
  `subagent_total_tokens` are all equal, with `exact` boundary coverage, renders a line stating that
  the measures agree, and a test pins it.
- **Effort:** M
- **Risk if fixed:** the reconciliation annotation appears on many more phases (every row where two
  measures were compared, not only where a non-`total_tokens` measure won), which changes the
  rendered `metrics.md` for most plans and may break tests asserting on the line's absence.

## G3 — Stop comparing a dispatched measure against an inline `total_tokens`

- **Kind:** bug
- **Severity:** high
  (Raised from medium on adversarial review: this is a measurement that misreports in shipped
  output, and its scope is wider than the `equal` branch — see Evidence.)
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:1793`
  and `:1800-1801` (`beaten = raw_tokens`), consumed by `_reconciliation_relation_clause` at
  `:661-683` and rendered under the preamble at `:2019-2025`
- **Evidence:** `beaten` is the row's raw `total_tokens` regardless of whether that field was ruled
  *ineligible* as cross-population at `:593` (`if field == 'total_tokens' and population ==
  POPULATION_INLINE: continue`). Given G2, an `inline`-population row is the **only** row that
  reaches the clause at all — so it is not just `=` that compares across populations, but `>` and
  `<` as well. Two probes against a pristine copy of the shipped module:
  - `{'total_tokens': 5000, 'total_tokens_population': 'inline', 'subagent_total_tokens': 5000}` →
    `4-plan → subagent_total_tokens 5,000 (= total_tokens 5,000; measures agree)`;
  - `{'total_tokens': 5000, 'total_tokens_population': 'inline', 'subagent_total_tokens': 3000}` →
    `4-plan → subagent_total_tokens 3,000 (< total_tokens 5,000)`, which
    `_reconciliation_relation_clause`'s own docstring calls "a genuine anomaly".

  Both render under the preamble "Tokens reconciled across the competing measures of the dispatched
  population", while the population annotation lower in the *same report* says the phase dispatched
  nothing and its `total_tokens` is the main-context-window measurement. The module states at
  `:483-486` that on an inline row "`total_tokens` carries a main-context measurement … so it is
  excluded — putting it in a dispatched-population max would be the very mislabel the discriminator
  exists to prevent", and `standards/data-format.md:306-310` repeats it. Both shipped D4 regression
  tests construct exactly this row shape (`test_dispatch_boundary_ledger_population.py:237-260` for
  `=`, `:262-278` for `<`), so the suite pins the unsound comparison rather than catching it.
- **Reachable on real data, not only in fixtures:** `enrich` writes `subagent_total_tokens` /
  `subagent_samples` first (`:3509-3513`) and only afterwards stamps
  `total_tokens_population = inline` on any row whose `total_tokens` is falsy at that moment
  (`:3579-3584`). A phase that *did* dispatch but never closed with `--total-tokens` therefore ends
  up carrying dispatched measures under an `inline` stamp — the exact row shape above.
- **Why it matters:** every relation this surface currently emits is a comparison between a
  main-context figure and a dispatched figure, announced as a reconciliation of "competing measures
  of the dispatched population". The `=` case is the loudest instance — a reader is told two
  independent producers agree when the module's own rule says the two are not comparable — but the
  `<` case is the more common one and carries the same defect, dressed as an anomaly report. This is
  the class of cross-population mislabel the epic exists to eliminate, emitted by the surface built
  to prove it had been eliminated.
- **Action:** make the clause state what it compared. Either suppress it whenever `total_tokens` was
  excluded from eligibility for population reasons, or render it as `(not comparable — total_tokens
  on this row measures the inline main-context population)`. Once G2 makes the same-population path
  reachable, re-point the D5(c) `=` and `<` tests at same-population rows.
- **Done when:** an `inline`-population row renders no `>` / `=` / `<` relation against
  `total_tokens` (or renders an explicit not-comparable clause instead), and the D4 regression tests
  for the `=` and `<` relations run against rows whose `total_tokens` is dispatched-population.
- **Effort:** S (render change) + M (test rework, gated on G2)
- **Risk if fixed:** `test_equal_boundary_and_total_annotated_as_agreement` and
  `test_smaller_dispatched_winner_annotated_as_below_total` both construct inline rows and will need
  rewriting; do not simply delete them, or D4 loses its regression coverage entirely. Sequencing
  matters: fixing G3 before G2 leaves the `=` branch with no reachable row at all.

## G4 — Add a drift guard tying `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` to the dispatching code

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** constant at
  `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:515-522`; the
  only guards are `test/plan-marshall/manage-metrics/test_dispatch_boundary_ledger_population.py:183-193`
  and `test/plan-marshall/manage-metrics/test_persisted_aggregate_round_trip.py:219`
- **Evidence:** the constant's preamble claims it is "Derived from the DISPATCHING code — the call
  graph in `ref-workflow-architecture/standards/call-graph.md` and the `record-dispatch-boundary`
  call sites in the phase workflow docs … NOT from any single run's emitted classes". Nothing
  enforces that. `test_exclusion_constant_is_source_derived_not_a_registering_phase` asserts
  membership for two of the six names and non-membership for the three registering phases — all
  against the same hand-written literal. A repository-wide search for any test reading `call-graph.md`
  or the workflow docs in connection with this constant returns nothing, while the same search
  pattern does return the analogous lock-step guard for `DISPATCH_TERMINATION_CAUSES` at
  `test/plan-marshall/manage-metrics/test_manage_metrics.py:3871-3876`, which discovers every
  enumeration site in the shipped doc and compares it to the tuple. The repository states the
  obligation explicitly at
  `marketplace/bundles/plan-marshall/skills/manage-metrics/SKILL.md:446` — "When adding a new
  full-set enumeration, either derive it from the tuple or add a structural-equality test, and
  prefer deriving". (The "Restating surfaces (lock-step obligation)" paragraph at
  `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:944` states the
  same obligation for the boundary-row *column schema* — a sibling enumeration, not this one.)
- **Why it matters:** the exclusion list is the ledger's *declaration of population*. If a workflow
  doc gains or loses a `record-dispatch-boundary` call, the constant silently stops describing the
  system, and the ledger goes back to excluding classes without saying so — the precise defect D3
  was written to close, restored by drift rather than by design.
- **Action:** add a structural-equality test in `test/plan-marshall/manage-metrics/` that scans the
  bundle for `record-dispatch-boundary` invocations, derives the registering `--phase` set, and
  asserts that (a) the registering set and `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` are disjoint and
  (b) their union equals the class list enumerated in `call-graph.md`. Prefer deriving the constant
  outright over mirroring it.
- **Done when:** deleting the `record-dispatch-boundary` block from
  `plan-marshall/workflow/execution.md` makes a test in `test/plan-marshall/manage-metrics/` fail.
- **Effort:** M
- **Risk if fixed:** the guard needs a robust way to enumerate classes from `call-graph.md`, which is
  ASCII-art prose; a brittle parser would produce false failures on unrelated diagram edits. Prefer
  scanning for the call sites (a precise pattern) and keeping the class total as an asserted
  constant with a named source.

## G5 — Perform the D3 negative control the plan specified

- **Kind:** test-gap
- **Severity:** medium
- **Topic:** tests
- **Where:** `test/plan-marshall/manage-metrics/test_dispatch_boundary_ledger_population.py:195-220`
  (`test_negative_control_dispatched_phase_shortfall_is_declared_not_silent`)
- **Evidence:** `plan.md` § Verification requires: "**D3's exclusion list is verified by a negative
  control**: remove a class's registration and confirm it appears in the list rather than silently
  shrinking the denominator." The test carrying that name removes no registration. It seeds a
  `4-plan` row with `rows: 1, samples: 2` and asserts `'PARTIAL: 1 of 2 dispatch(es) recorded'`,
  `'excluded by declaration' in report` and `'q-gate-validation' in report`. The last two assertions
  hold for *any* report with a boundary surface, because the declaration block at `:2112-2122` is
  unconditional — so they cannot distinguish a phase-specific shortfall from the global banner.
- **Why it matters:** the control as specified is the only check that would have caught G4. Run
  literally against the shipped code it would fail — removing a class's registration does not add it
  to a hard-coded literal — so the deliverable's stated verification was not merely skipped, it was
  replaced by one the implementation could pass.
- **Action:** once G4's derivation guard exists, implement the control as written: remove a class's
  registration (in a fixture copy of the workflow surface, or by parameterising the derivation), and
  assert the removed class appears in the rendered exclusion list. Rename the current test to what it
  actually checks (a partial-coverage row renders both the PARTIAL note and the declaration).
- **Done when:** a test exists whose failure mode is "a class stopped registering and did not appear
  in the exclusion list", and the existing test's name matches its assertions.
- **Effort:** M
- **Risk if fixed:** depends on G4; implementing it before the constant is derivable will produce a
  test that can only be satisfied by editing two places at once, which is the drift it is meant to
  prevent.

## G6 — Carry the change-type-fallback fold onto the shipped surfaces

- **Kind:** incomplete
- **Severity:** low
  (Re-severitied from medium on adversarial review. The original entry rested on the fallback being
  "un-named"; it is in fact named and folded in `report-01.md:43` — "phase-3-outline (main envelope,
  + change-type LLM fallback)" — so the D1 derivation is sound and the shortfall it causes *is*
  explained by the named class `phase-3-outline`. What remains is a disclosure gap on the shipped
  surfaces, which restate a bare total of "9" with no record of the fold: a stale-in-effect claim
  confined to a comment and a standards sentence.)
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:512-522`
  (the "Of the 9 dispatch classes" comment and the constant) and
  `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:346-350`
- **Evidence:** `ref-workflow-architecture/standards/call-graph.md:152-158` draws a distinct
  orchestrator-side dispatch before the phase-3 envelope: "`/manage-status change-type-heuristic/`
  (script — keyword classifier) │ ambiguous ╵┄═► `execution-context` (LLM fallback — uses effort, no
  role key)". `plan-marshall/workflow/planning-outline.md:273-275` confirms it is a separate dispatch
  whose `<usage>` must be summed into the `3-outline → 4-plan` boundary: "…and any LLM fallback
  dispatched from `manage-status:change-type-heuristic` when its heuristic returned `ambiguous`". It
  issues no `record-dispatch-boundary`, it resolves under no role key, and it appears in neither the
  count of 9 nor `DISPATCH_BOUNDARY_EXCLUDED_CLASSES`.
- **Why it matters:** D3's rule is that a non-registering class must be *named*, because "an un-named
  omission is indistinguishable from a class that did not run". This class is un-named, and both the
  code comment and the shipped standards doc assert a total ("9 dispatch classes") that a later
  reader will treat as the derived population.
- **Action:** either add `change-type-fallback` to `DISPATCH_BOUNDARY_EXCLUDED_CLASSES` and restate
  the totals as 10 classes / 3 registering / 7 excluded in both the code comment and
  `data-format.md`, or state explicitly, at both sites, that the fallback is folded into
  `phase-3-outline` and why.
- **Done when:** the enumerated class total and the exclusion list account for the change-type
  fallback, and `manage-metrics.py` and `data-format.md` state the same figures.
- **Effort:** S
- **Risk if fixed:** changing the rendered exclusion list changes `metrics.md` output and the
  persisted `dispatch_boundary_excluded_classes` value;
  `test_persisted_aggregate_round_trip.py:219` and
  `test_dispatch_boundary_ledger_population.py:171-181` both read it.

## G7 — Correct the "states the measure's coverage on every render" claim

- **Kind:** doc-defect
- **Severity:** medium
- **Topic:** bundle-docs
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md:333-336`
- **Evidence:** the text reads "The `Dispatch-boundary total` bullet states the measure's coverage on
  every render (complete / partial / undecidable / **failure** over-coverage) and whether it won the
  maximum." Rendering a phase with `dispatch_boundary_rows_recorded: 8`, `subagent_samples: 3` and no
  non-zero boundary sum produced no such bullet at all (see G1). The adjacent bullet at `:337-338`
  covers only "When the boundary file is absent (no rows)", so the rows-present/sum-zero case is
  described by neither.
- **Why it matters:** this is the standards document consumers read to decide what a missing bullet
  means. As written, an absent bullet reads as "the boundary file was absent", when it may instead
  mean "the file held rows whose coverage is a failure". A false claim in shipped documentation makes
  the silent failure in G1 harder to notice, not easier.
- **Action:** fix G1 so the claim becomes true; if the guard is left as-is, amend the sentence to
  state the exact condition under which the bullet renders.
- **Done when:** the sentence at `data-format.md:333-336` is true of `cmd_generate`'s behaviour for
  every combination of `dispatch_boundary_rows_recorded`, `dispatch_boundary_total` and
  `subagent_samples`.
- **Effort:** S
- **Risk if fixed:** none beyond keeping the doc in step with G1.

## G8 — Remove or use `_boundary_measure_is_partial`

- **Kind:** omission
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:565-576`
- **Evidence:** the docstring says "Thin wrapper over `_boundary_coverage_state` **preserved for
  callers that only need the under-coverage bit**". A repository-wide search finds no production
  caller: the only references are four assertions in
  `test/plan-marshall/manage-metrics/test_manage_metrics_record_dispatch_boundary.py:146-166`.
- **Why it matters:** it is dead production code whose docstring asserts a caller population that
  does not exist, and four tests that certify only the dead path — cost with no coverage value, and a
  false statement in a module whose whole subject is claims matching their populations.
- **Action:** delete the wrapper and its four assertions, or (if a caller is intended) name it. If
  kept, correct the docstring to say it is exercised by tests only.
- **Done when:** either the symbol is gone along with its tests, or a production call site exists.
- **Effort:** S
- **Risk if fixed:** an external consumer importing the private helper would break; the leading
  underscore and the empty search result make that unlikely.

## G9 — Make the coverage figure reference the exclusion declaration

- **Kind:** incomplete
- **Severity:** low
- **Topic:** measurement/metrics
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py:2199-2203`
  (the `partial` coverage text) versus the declaration block at `:2112-2122`
- **Evidence:** `plan.md` D3's *Done when* requires "an explicit exclusion list **that the coverage
  figure references**". The implemented reference runs the other way: the declaration block says "A
  phase whose boundary rows fall short of its subagent_samples is short by exactly these excluded
  classes", while the PARTIAL coverage text in Phase Details reads only "PARTIAL: {n} of {m}
  dispatch(es) recorded, so this measure is a floor and is ineligible for the reconciliation
  maximum" — no pointer to the declaration, which sits in a different section of the document.
- **Why it matters:** a reader who lands on the Phase Details bullet sees a bare shortfall with no
  indication that it is expected and declared. That is a weaker version of the silent-exclusion
  defect: the declaration exists but is not findable from the figure it explains.
- **Action:** append a short pointer to the `partial` (and `over`) coverage strings, e.g. "— see the
  declared dispatch-boundary exclusions above".
- **Done when:** the PARTIAL coverage text names or points at the declared exclusion list, and a test
  asserts the pointer.
- **Effort:** S
- **Risk if fixed:** the coverage string is asserted verbatim by
  `test_dispatch_boundary_ledger_population.py:217` (`'PARTIAL: 1 of 2 dispatch(es) recorded'`);
  appending text after that prefix keeps the assertion valid.
