# PLAN-19: Execute-lane verification loop

> ✅ **Staged 2026-09-28 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-19-execute-verification-loop.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make phase-5's per-deliverable verification loop converge on a known failure instead of paying
for it once per deliverable. The PLAN-13 run paid six 7–17-minute orchestrator-tier module-test
runs and five `verification-feedback` dispatches, all re-triaging one failure
(`test_lessons_pipeline_regression.py:60`) that was already mapped to pending fix task TASK-11.

## Deliverables

1. **A fix task created by verification-feedback is schedulable.** TASK-11 carried
   `envelope_id: null`. The executor runs only tasks whose `envelope_id` equals the current
   envelope, so no envelope dispatch would ever run it, and the orchestrator had to dispatch it
   with `envelope_id: null`, which no document describes. Assign an envelope at creation, or
   define the null-envelope dispatch. Schedule the fix task ahead of the remaining deliverables
   whose builds it blocks. Make `manage-tasks get` surface `envelope_id` (today only `next` does).
2. **Known-failure short-circuit.** `execution.md` routes every build error through a fresh triage
   dispatch, even when the finding is byte-identical to one a pending fix task already owns. Add
   the short-circuit, and say that the build wrapper already persists each failing test as a finding
   (twice per run: once for the inner command, once for the outer executor command). On the first
   failure the orchestrator hand-filed a third, qgate-scoped copy (`8ffb06`).
3. **End-of-execute re-dispatch rules agree.** The orchestrator-tier table says a green build means
   "Re-dispatch phase-5-execute so the leaf resumes; the freshness gate (Step 12a) now sees the stamp".
   The pre-dispatch queue peek in the same file says "MUST NOT re-dispatch" when `loop-exit-guard`
   reports pending=0 / in_progress=0. At the end of execute both apply, and Step 12a was never
   re-entered. Make one rule win explicitly, and keep the freshness gate reachable.
4. **A module_testing task is not `done` before its test ran.** `finalize-step` auto-closes a task
   when its last step closes, so TASK-2/4/6/8/10 read `done` before the orchestrator-tier
   module-tests run, which is their only verification. A failure then has no task to reopen. Keep
   such a task open until its verification build reports, or give the failure a defined reopen path.
5. **Triage fix tasks can be holistic.** `plan-marshall/workflow/triage.md:191` prescribes
   `deliverable: 0` (the holistic-task sentinel `_cmd_qgate_mechanical.py:261` already honours),
   but `manage-tasks commit-add` refuses it as "Missing required field: deliverable"
   (`_tasks_core.py:886`), so the triager guessed owning deliverables (D4, D1). Accept `0`
   explicitly. Regression test: `commit-add` with `deliverable: 0` succeeds; a genuinely absent
   field still refuses.

## Claim Labels

- OBSERVED: six module-test runs + five verification-feedback dispatches on one known failure; TASK-11 `envelope_id: null` — cited at `inbox/archive/plan-13-finalize-mechanism-defects/plan-13-finalize-mechanism-defects-004.md` §§ 1–2 (run report)
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: _tasks_crud.py cmd_commit_add L261-275 writes no envelope_id; _tasks_query.py cmd_read L117-135 omits it (only cmd_next L271); execution.md L171/178 envelope_id filter
- OBSERVED: the two contradictory re-dispatch rules — cited at `plan-13-…-004.md` § 3; HYPOTHESIS that both sentences sit in `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — confirm/refute at that file § orchestrator-tier table and § pre-dispatch queue peek (verify-at-outline)
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: execution.md L376 orchestrator-tier success re-dispatch (freshness Step 12a) vs L258 pre-dispatch peek MUST NOT re-dispatch at pending=0/in_progress=0
- OBSERVED: build findings persisted twice per failing test — cited at `plan-13-…-004.md` § 4; HYPOTHESIS for the producer — confirm/refute at the build wrapper's findings-persist call (verify-at-outline)
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: _build_shared.py cmd_run_common L921-937 rebuilds the inner run's routed_errors and calls _store_build_findings again; daemon child re-runs the executor (_build_execute_factory.py L99-101)
- OBSERVED: module_testing tasks auto-closed before verification — cited at `plan-13-…-004.md` § 6
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: _cmd_step.py cmd_finalize_step L112-114 sets status=done once all steps are terminal; no module_testing branch
- OBSERVED: `triage.md:191` prescribes `deliverable: 0`; `_tasks_core.py:886` raises "Missing required field: deliverable" — both read at HEAD by the orchestrator; rejection of `0` specifically is the run's report (`plan-13-…-004.md` § 23), resolved at cleanup 2026-09-28: `_tasks_core.py` `_build_task_record` coerces None/blank to 0 and refuses 0 unless `origin=='holistic'`, while `triage.md` sets no origin
  - verdict: corroborated | checked_at: c56710b36f01f05be781ff9fb73dbf91b93f5706 | by: process-compliance/cleanup | rescoped: n/a | evidence: _tasks_core.py _build_task_record L881-886 coerces None/blank to 0 and refuses 0 unless origin=='holistic'; triage.md L191 prescribes deliverable: 0 with no origin

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` — short-circuit, re-dispatch rule
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/triage.md` — fix-task creation
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/` — envelope scheduling, task auto-close
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_core.py` — `deliverable: 0`, `envelope_id` in `get`
- OBSERVED: `test/plan-marshall/manage-tasks/` — regression tests
- OBSERVED: `test/plan-marshall/phase-5-execute/` — scheduling / auto-close tests
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_query.py` — `cmd_read` (serves `get`) omits `envelope_id` (D1) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_tasks_crud.py` — `commit-add` assigns no envelope (D1) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_step.py` — `cmd_finalize_step` auto-close (D4) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — double finding persistence (D2) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/verification-feedback.md` — fix-task creation (D1) (added cleanup 2026-09-28, re-grounding at c56710b — understated surface)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-10 (staged; may share `execution.md`), PLAN-20 / PLAN-21 (none expected — finalize surfaces). Check the gate.
- Scope-bloat guard: 5 deliverables.

## Folded inbox material (same act)

- `plan-13-finalize-mechanism-defects-004.md` items 1, 2, 3, 4, 6, 23 (first half): deliverables 1–5

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-19-execute-verification-loop.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
