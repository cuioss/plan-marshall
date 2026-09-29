# PLAN-21: Finalize step roster, firing accounting and re-fire currency

> ✅ **Staged 2026-09-28 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-21-finalize-step-accounting.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make phase-6's per-step records true and its re-fires proportionate. In the PLAN-13 run:
- the roster placed two self-dispatching steps in the dispatched lane;
- a re-stamp counted as a second firing;
- a docs-only commit re-fired every head-dependent step in full, because no step declares
  `verdict_inputs`;
- plugin-doctor gated the declared footprint and missed a finalize-time widening;
- a dispatch's usage was recorded before it arrived.

## Deliverables

1. **Roster matches the step bodies.** `phase-6-finalize/standards/dispatch-inline-split.md` lists
   `default:finalize-step-simplify` (line 27) and `default:pre-submission-self-review` (line 21) as
   DISPATCHED. Both step documents issue their own `Task:` dispatches (simplify Step 3; self-review
   Steps 2 and 3b, "from the inline dispatcher context"), and a dispatched leaf cannot dispatch.
   Move them to the inline lane, or remove their inner dispatches. Add a closure test: no step in the
   dispatched lane contains a `Task:` dispatch. Put it beside the existing split roster-closure tests
   `test/plan-marshall/phase-6-finalize/test_dispatch_roster_closure_{closure,roster,cli}.py`.
2. **A re-stamp is not a firing.** The item-5f `head_at_completion` re-stamp (`--no-completion-log`)
   for `finalize-step-simplify` bumped `firing_count` to 2 and appended a `prior_firings` entry for a
   step that fired once. Make firing accounting ignore the re-stamp path. Regression test included.
3. **Head-dependent steps declare `verdict_inputs`.** `verdict_currency classify` returned
   `invalidated / verdict_inputs_undeclared` for lessons-housekeeping, simplify and plugin-doctor
   after a docs-only 9-file fix commit. All three re-ran in full, including a ~10-minute plugin-doctor
   pass. The preservation mechanism exists (`verdict-currency.md`), but no step opts in. Declare
   `verdict_inputs` for each head-dependent step, so that a commit outside a step's inputs preserves
   its verdict. ⛔ **Carve-out (cleanup 2026-09-28):** `.claude/skills/finalize-step-plugin-doctor/SKILL.md`
   L48-57 records an evidence-based REFUSAL to declare `verdict_inputs`, because its `broken-relative-link`
   and agentfile walks read outside any glob. Honour that refusal, or supersede it with a declaration
   covering those walks. Never override it silently.
4. **plugin-doctor gates the realized footprint.** After an operator-approved sweep added 35 files in
   ~12 more skills, plugin-doctor kept gating only the 8 skills derivable from
   `references.affected_files` (27 entries). `sync-affected-files` re-derives from the solution outline
   only, so a finalize-time scope widening is never gated structurally. Gate on the realized footprint,
   or the union of declared and realized.
5. **Records wait for their inputs, carry their identity, and retired fields are not read.** (a) In iteration 5 the orchestrator
   recorded accumulate / record-dispatch-boundary / record-step with an estimated verifier share
   before the verifier's `<usage>` arrived. The accumulator could only be topped up (+620 tokens), and
   the row's duration stays overstated by 15,622 ms. Forbid recording a boundary before every dispatch
   inside it has reported. (b) lessons-housekeeping Step 1 reads
   `manage-references get --field modified_files`, which returns `field_retired` and falls back to
   `compute-footprint` (lesson 2026-09-27-08-001 records it). Read the live field. (c) *(folded
   2026-09-29, reclaimed from the parked PLAN-TRUTH-175)* 25 of 30 `6-finalize` and 8 of 9 `5-execute`
   dispatch-boundary rows were recorded without `--step-id`, so `check-dispatch-audit` paired only 3 of
   30 finalize dispatches with their `record-step` rows. `[DISPATCH]` lines exist for only 4 of 7
   dispatched finalize steps (`missing_dispatch_emission: 3`, `confidence: low`). Make `--step-id` part
   of the literal `record-dispatch-boundary` invocation in the phase-6-finalize dispatcher and
   `execution.md`. The recorder warns or refuses when it is absent for `6-finalize`. Every finalize
   dispatch resolves with `--workflow`, so the seam emits `[DISPATCH]` itself. Test: dispatched finalize
   steps == finalize-dispatcher `[DISPATCH]` lines on a fixture run.

## Claim Labels

- OBSERVED: `dispatch-inline-split.md` lines 21 and 27 list both steps as dispatched — read at HEAD by the orchestrator; that both step documents contain their own `Task:` dispatches is the run's report (`inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-004.md` § 7), HYPOTHESIS — confirm/refute at the simplify and pre-submission-self-review step documents under `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/` (verify-at-outline)
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: dispatch-inline-split.md L21/L27 list both as dispatched; Task: dispatches in standards/finalize-step-simplify.md and workflow/pre-submission-self-review.md Steps 2+3b
- OBSERVED: re-stamp counted as a firing — cited at `plan-13-…-004.md` § 10
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: _cmd_mark_step.py L615-630 same-outcome head change calls _extend_firing_history; --no-completion-log only suppresses the log line (L332)
- OBSERVED: `verdict_inputs_undeclared` for three steps after a docs-only commit — cited at `plan-13-…-004.md` § 11; no step frontmatter declares `verdict_inputs` (re-grounded at c56710b; the mention list also includes `phase-6-finalize/scripts/verdict_currency.py` and the plugin-doctor refusal — the earlier 'only in' list was incomplete)
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: no step frontmatter declares verdict_inputs; mention list also includes verdict_currency.py and the plugin-doctor SKILL.md L48-57 deliberate refusal
- OBSERVED: plugin-doctor gated 8 declared skills vs ~12 realized — cited at `plan-13-…-004.md` § 16 and landing `-007` § Residue
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: .claude/skills/finalize-step-plugin-doctor/SKILL.md Step 1 L63-66 gates on affected_files; _references_crud.py L22-28 affected_files is the outline-declared set
- OBSERVED: usage recorded before arrival (+620 tokens, 15,622 ms) — cited at `plan-13-…-004.md` § 18
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: phase-6-finalize/SKILL.md items 5b/5c L1091-1128 no rule against recording a boundary before inner dispatches report; accumulator additive
- OBSERVED: keyless dispatch-boundary rows (25/30 finalize, 8/9 execute) and `missing_dispatch_emission: 3` — cited at `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-006.md` § Evidence (plan-retrospective aspects)
- OBSERVED: `modified_files` returns `field_retired` — cited at `plan-13-…-004.md` § 13, lesson `2026-09-27-08-001`
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: lessons-housekeeping SKILL.md Step 1 L89-91 reads --field modified_files; _references_core.py L125 RETIRED_REFERENCE_FIELDS={'modified_files'}

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md` — roster
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/verdict-currency.md` — opt-in
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/scripts/verdict_currency.py` — classifier (D3) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/extension-api/standards/ext-point-finalize-step.md` — `verdict_inputs` superset rule (D3) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-simplify.md` — inner `Task:` dispatch (D1) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/workflow/pre-submission-self-review.md` — inner `Task:` dispatches, Steps 2 and 3b (D1) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` — item 5f re-stamp, boundary recording
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/` — firing accounting
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-references/scripts/` — realized-footprint gating input
- OBSERVED: `.claude/skills/finalize-step-plugin-doctor/` — footprint scoping, `verdict_inputs`
- OBSERVED: `.claude/skills/finalize-step-lessons-housekeeping/` — retired field, `verdict_inputs`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/scripts/manage-metrics.py` — `record-dispatch-boundary` `--step-id` (D5c, folded 2026-09-29)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — literal `--step-id` on execute dispatch records (D5c, folded 2026-09-29)
- OBSERVED: `test/plan-marshall/manage-metrics/` — `--step-id` enforcement test (D5c, folded 2026-09-29)
- OBSERVED: `test/plan-marshall/phase-6-finalize/` — roster closure test
- OBSERVED: `test/plan-marshall/manage-status/` — firing accounting test

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-20 (shares `phase-6-finalize/SKILL.md` and `standards/`); truthful-signals PLAN-TRUTH-175 is PARKED (PM-MCP), so its `[DISPATCH]` / `--step-id` facet is reclaimed here as D5c (2026-09-29). Sequence after PLAN-20.
- Scope-bloat guard: 5 deliverables.

## Folded inbox material (same act)

- `plan-13-finalize-mechanism-defects-004.md` items 7, 10, 11, 13, 16, 18: deliverables 1–5

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-21-finalize-step-accounting.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
