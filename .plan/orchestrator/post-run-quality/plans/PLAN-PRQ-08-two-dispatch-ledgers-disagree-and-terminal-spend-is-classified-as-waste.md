# PLAN-PRQ-08: Two dispatch ledgers disagree, nothing in the report reconciles them, and terminal spend is classified as waste

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/post-run-quality-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: post-run-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Provenance

Staged 2026-09-17 from the same corpus classification sweep as `PLAN-PRQ-09`. Six lessons, filed by five
different plans between 2026-08-27 and 2026-09-08, all preserved in this epic at
`.plan/orchestrator/post-run-quality/lessons/{id}.md`. Three of them (`2026-08-27-16-002`,
`2026-09-04-08-010`, `2026-09-05-07-002`) state one defect three times — the recurrence is the evidence.

⛔ **Folded 2026-09-22 from inbox `lessons-handling-26-09-22-01-001.md`, cross-ref pair `2026-09-20-08-006`
(primary) / `2026-09-21-13-001`.** A seventh and eighth occurrence of the same underlying gap, viewed from
both sides of the boundary: every one of the 12 `6-finalize` rows in the execution manifest's
`execution_log` carries `total_tokens: unmeasured` / `tool_uses: unmeasured` / `duration_ms: unmeasured` —
no `work/metrics-dispatch-boundaries-6-finalize.toon` is written at all, though the equivalent files exist
for `4-plan` and `5-execute` (the consumer-side symptom D0's corpus derivation should now count); and
`plan-retrospective`'s own Phase Dispatch Boundaries section is unreachable because its trigger key is
never registered (the producer-side symptom — "no aspect consumes it", exactly this spec's own Objective
sentence). Expected Surface updated in the same edit to add the phase-6-finalize boundary-ledger producer,
which the existing declaration did not name.

## Objective

**A plan's spend is recorded in two ledgers that disagree, no aspect reconciles them, and the one figure
the report does publish about terminal dispatches calls productive work waste.** The reconciler already
exists and is correct: run by hand on one plan, `manage-metrics reconcile-ledgers` returned **24 findings
over 32 union rows**, including three dispatches worth **603,578 tokens (12.9% of that run's 4.68M)** that
no `execution_log` row names. None of it reaches the compiled retrospective, because no aspect consumes it.

Alongside that, the published error/retryable token classes do not mean what a cost reader is told they
mean: findings-producing self-review firings were stamped `error`, **inflating the reported waste figure by
2.32M tokens** on one run.

⭐ This is `PLAN-PRQ-02`'s shape at the ledger tier: there, a producer published a number over a population
it never read; here, two populations exist, disagree, and the report picks one without saying so.

## Deliverables

Five deliverables. D0 is a gate.

**D0 — GATE: derive the row populations and the disagreement rate across the archived corpus.** Run the
existing `reconcile-ledgers` over every archived plan and publish: union rows, per-class finding counts
(`row_absent_from_execution_log`, `row_absent_from_boundary_ledger`, `boundary_never_closed`,
`phase_re_entered`), and the token mass each class hides. ⛔ One plan's 24 findings is an instance; the
corpus figure is what tells you whether this is systemic. The reconciler is read-only, so this costs a
sweep and no risk.

**D1 — A retrospective aspect consumes `reconcile-ledgers`.** The producer exists, is documented, is
read-only, and nothing reads it. Register it so its findings reach the compiled report with their
populations. (Lesson `2026-09-08-22-006`.)

**D2 — `refire-report` counts the ledger that actually records re-fires.** It reads only `execution_log`,
which under-counts precisely the steps that re-fire most — so the report's re-fire figure is smallest
exactly where re-firing is worst. (Lesson `2026-09-03-23-001`.)

**D3 — Terminal-dispatch spend is classified by what the dispatch PRODUCED, not by how it terminated.** A
firing that returned findings and then hit its ceiling is not waste; stamping it `error` inflated one run's
waste figure by 2.32M tokens, and the same misclassification is recorded three times across the corpus.
Publish an honest partition: the classes must sum to the dispatched total and each must state what it
counts. (Lessons `2026-08-27-16-002`, `2026-09-04-08-010`, `2026-09-05-07-002`.)

**D4 — The anchor comparison happens where it can still change the outcome, plus controls.** Finalize
re-fire spend is unbounded and the plan-efficiency anchor comparison runs only post-merge, so four plans
exceeded their anchors by **3.6×–6.5×** with nothing observing it in time. (Lesson `2026-09-04-08-009`.)
⛔ **FOLDED 2026-09-18** (inbox message `truthful-signals-001.md`, forwarded from `truthful-signals` at
the end of its own corpus sweep): the SAME clock, one phase earlier. `phase-4-plan` never consults the
`(scope_estimate, change_type)` anchor table (`plan-retrospective/references/plan-efficiency.md` § 2)
before composing tasks, so a plan can be sized an order of magnitude past its own grading anchor before
any post-merge comparison ever runs — confirmed on lesson `2026-09-15-08-003`: one 12-deliverable,
44-task plan ran 5.2× over its `multi_module+bug_fix` anchor (10,488,689 vs 2.0M tokens), discovered only
after the spend. D4 now also covers: `phase-4-plan` reads the anchor table and surfaces a split proposal
when the composed task set projects past the warning column, BEFORE execution — not merely detecting the
overrun post-merge as originally scoped. Controls: a reconciled pair reports agreement, a genuinely-absent
row still reports absent, each corrected class is pinned by a case where old and new figures differ, AND a
plan that would have exceeded its anchor is shown to have been offered a split proposal at phase-4-plan.

## Claim Labels

Every figure below is OBSERVED by the plan that filed the cited lesson; all six lessons are preserved in
this epic. ⛔ Re-ground each against the named surface at HEAD before scoping (verify-at-outline).

⛔ **ADDED 2026-09-18 (cleanup, `checked_at: 1605831c5`) — all six cited lessons are already retired from
the live corpus.** `2026-09-08-22-006`, `2026-09-03-23-001`, `2026-08-27-16-002`, `2026-09-04-08-010`,
`2026-09-05-07-002` and `2026-09-04-08-009` all carry `superseded` tombstones dated `2026-09-18T06:17Z`
("moved into epic post-run-quality; text preserved verbatim…"). This plan inherits `PLAN-PRQ-09`'s guard,
which this spec did not originally carry:

1. **Read them from `lessons/{id}.md`, never from the corpus** — `manage-lessons get` will return
   `not_found` for all six, and that `not_found` is correct.
2. ⛔ **This plan MUST NOT call `manage-lessons remove` on any id it cites.** They are already retired, and
   `remove` on an absent id is the documented path that destroys a DIFFERENT lesson when retried. There is
   no lesson-retirement work in this plan — retirement was completed by the sweep that staged it.

⚠ Note `2026-09-08-22-006` (this spec's D1 lesson) has **no tombstone at all** — it is a headerless,
unretirable entry per `PLAN-PRQ-05`'s fold. ⛔ **CORRECTED 2026-09-22 (cleanup, `checked_at: 7d82d5d90`):
"only surviving copy" is wrong at HEAD** — TWO tracked copies exist,
`lessons/2026-09-08-22-006.md` and `lessons/invalid-headerless/2026-09-08-22-006.md`; `manage-lessons get
2026-09-08-22-006` still correctly returns `not_found`, so the MUST-NOT-call-`remove` guard above is
unaffected by the correction.

- OBSERVED (lesson `2026-09-08-22-006`): `reconcile-ledgers` returned 24 findings over 32 union rows on one
  plan — 3 × `row_absent_from_execution_log` totalling 603,578 tokens, 17 × `row_absent_from_boundary_ledger`,
  1 × `boundary_never_closed`, 2 × `phase_re_entered` — and none reaches the report.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: producer live and unconsumed at _ledger_reconciliation.py:114-117 (4 finding classes). MATERIAL CHANGE since e8a71650: check-dispatch-audit.py D4 now reads boundary-ledger rows directly and names reconcile-ledgers as owning divergence findings -- claim holds literally but D1 narrows from 'wire a producer nothing reads' to 'replace a partial re-derivation with the producer'
- OBSERVED (lesson `2026-09-03-23-001`): `refire-report` reads only `execution_log`.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: summarize_refires at manage-execution-manifest.py:2929 iterates execution_log rows alone, no boundary-ledger read. NARROWING: :2954-2960 already separates loop_backs/failures/errors into three columns -- D3's thesis already implemented on the refire-report side; D2's residue is the missing second ledger, not the outcome classification
- OBSERVED (lessons `2026-08-27-16-002`, `2026-09-04-08-010`, `2026-09-05-07-002`): the error/retryable
  token classes misattribute terminal dispatch spend; one run's waste figure was inflated by 2.32M tokens.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: both halves check out: lessons/2026-08-27-16-002.md confirms error_total_tokens 2323435 (39%) all pre-submission-self-review, 26 real findings all fixed -- productive work stamped waste. Structural half derivable from logging-gap-analysis.md:193-195,228-242: no residual published, blocked_user_review lands in neither published class. D3 premise corroborated on current source
- OBSERVED (lesson `2026-09-04-08-009`): four plans missed their efficiency anchors by 3.6×–6.5×, observed
  only post-merge.
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: lesson 2026-09-04-08-009 present, manage-lessons get correctly returns not_found as the guard predicts. Anchors surface live. 4-plan 3.6x-6.5x measurement is a historical corpus reading absent at HEAD -- no current source supports or refutes. D4's FOLDED half confirmed: 0 plan-efficiency hits in phase-4-plan/**
- ⚠ HYPOTHESIS: the two ledgers' disagreement is systemic rather than plan-specific — D0 measures it, and
  a low corpus rate re-scopes D1/D2 downward (verify-at-outline).
  - verdict: unverifiable | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: D0's own corpus sweep, deliberately not executed in a read-only claim-check pass. reconcile-ledgers confirmed read-only/invocable. Re-scoping trigger stands and is reinforced by claim 0's narrowing -- D1's remaining delta may be smaller than staged
- ⛔ NOT THIS PLAN'S: the four unwired context-load flags (`record-dispatch-boundary`) are owned by
  `truthful-signals` PLAN-TRUTH-160, which folded that exact lesson on 2026-09-17. D0's sweep will see the
  empty columns — report them, do not fix them here.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: PLAN-TRUTH-160 staged in live truthful-signals queue, still carries its FOLDED block naming the four flags and call sites -- boundary holds (D0 reports, does not fix). NEW: PLAN-TRUTH-175 (staged) declares the identical fix with the OPPOSITE root cause and records overlaps:none -- sole-ownership reading no longer safe, cross-epic collision to record
- ⭐ CORROBORATING EVIDENCE, folded 2026-09-21 (inbox `retrospective-aspects-publish-verdict-005.md`,
  filed by `PLAN-PRQ-02`'s own retrospective, PR #1550): first-party post-landing confirmation of D0's
  premise, NOT a new fix — the message explicitly defers to this D0. On that run: `ledger_present: true`,
  `ledger_readable: true`, `ledger_rows_scanned: 796`, `summed_rows: 0`, `build_count: 0`,
  `total_build_seconds: unavailable`, while the plan's own script log recorded 27 build calls. The
  change-ledger build-row WRITER does not record build executions — no read-side fix can repair this.
  D0's corpus sweep should expect this same absence on every plan; D0's acceptance test can use this run's
  own baseline (`summed_rows == 27` after the writer is fixed).
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: archived inbox retrospective-aspects-publish-verdict-005.md carries every cited figure verbatim (796 rows scanned, 0 summed, 27 actual build calls); root cause and deferral to PRQ-08 D0 both explicit. PLAN-TRUTH-175 D5 now declares the identical build-time-oracle investigation on manage-change-ledger/** -- second collision to record
- ⭐ CORROBORATING EVIDENCE, folded 2026-09-21 (inbox `retrospective-aspects-publish-verdict-006.md`,
  same source): confirms the `record-dispatch-boundary` gap cited above — on that run, `context_position_cost`
  reported `total_rows: 103`, `measured_rows: 0`, `unmeasured_rows: 103` across every phase, and every one
  of the 103 rows named all four missing component fields (`input_tokens`, `output_tokens`,
  `cache_read_input_tokens`, `cache_creation_input_tokens`) in its own `unmeasured_columns`. Reinforces that
  the gap is structural (0-of-N on every plan), not incidental to one run — still `truthful-signals`
  PLAN-TRUTH-160's subject, not this plan's.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: post-run-quality/cleanup | rescoped: n/a | evidence: archived inbox retrospective-aspects-publish-verdict-006.md verbatim: 103 total rows, 0 measured, structurally unmeasurable on every plan using the current recorder -- matches 'not incidental to one run'. Same PLAN-TRUTH-175 D3 ownership contest as claim 5 applies

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/` — `reconcile-ledgers` and the spend classes (D0, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — the `record-dispatch-boundary` call site (~L1112) that writes `work/metrics-dispatch-boundaries-6-finalize.toon`; added by the 2026-09-22 fold (`2026-09-20-08-006`/`2026-09-21-13-001`) for the boundary-ledger absence at this phase (D0)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/standards/data-format.md` — the published class contract (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/retro_sections.py` — aspect registration (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/references/` — the plan-efficiency anchors (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-4-plan/SKILL.md` — where D4's pre-execution
  anchor consult and split proposal are added (folded 2026-09-18 from `truthful-signals-001.md`; confirmed
  at HEAD: no `plan-efficiency`/anchor reference exists in this file today)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-execution-manifest/scripts/manage-execution-manifest.py` — `refire-report` (D2)
- OBSERVED: `test/plan-marshall/manage-metrics/` — D4's controls
- OBSERVED: `test/plan-marshall/plan-retrospective/` — the aspect-registration control (D1)

## Dependencies and Sequencing

- Depends on: none. D0's sweep is read-only and can run immediately.
- ⛔ Shares `plan-retrospective/scripts/` with `PRQ-01`, `PRQ-02`, `PRQ-09`, and `manage-metrics/**` with
  `truthful-signals` PLAN-TRUTH-160 — the second is **cross-epic and invisible to both gates**. Check that
  epic's queue before launching.
- ⚠ `refire-report` sits in `manage-execution-manifest`, which `PRQ-06` and `truthful-signals` `-145`/`-147`
  also touch. Sequence.
- `phase-4-plan/SKILL.md` (D4, folded 2026-09-18) is a NEW surface for this spec; no sibling PRQ spec or
  known `truthful-signals` plan declares it as of this fold — unshared as far as either gate can see.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/post-run-quality/plans/PLAN-PRQ-08-two-dispatch-ledgers-disagree-and-terminal-spend-is-classified-as-waste.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
