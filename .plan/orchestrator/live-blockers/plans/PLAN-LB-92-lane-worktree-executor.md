# PLAN-LB-92: A runbook-lane worktree has its own executor, so routed builds and the plan's own new verbs run without a question

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-92-lane-worktree-executor.md` and is queued as one row file, `queue/PLAN-LB-92.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged 2026-10-23 on the operator's instruction ("the executor in worktree defect ... make it the next plan"). It is the
> root of the Open Defect "a plan whose own lane text calls a verb it introduces cannot run it", recurring in
> PLAN-LB-85 and PLAN-LB-88 (an operator question and a hand-run executor regeneration each time), and of the
> `executor_absent_from_worktree` fallback every runbook-lane build has recorded since PLAN-LB-78.

## Objective

A runbook-lane worktree is created without `.plan/execute-script.py`. Every routed build therefore falls back to
in-process, and a plan that adds a script verb cannot run it from its own worktree: the run asks the operator, then
regenerates the executor by a direct interpreter call that the guard refuses. PLAN-LB-73 D4 made the lane check for the
missing executor and record `executor_absent_from_worktree`; that is a disclosure, not a fix. This plan makes worktree
creation for the lane produce the executor, gives the run a verb that refreshes it after the plan changes the script
set, and makes the lane route builds through it.

## Deliverables

1. **A lane worktree is created with its executor, confirmed on disk.**
   - The lane's worktree creation produces `{worktree}/.plan/execute-script.py` through the seam the lifecycle already uses (`prepare_execute._generate_worktree_executor`: generation with `--marketplace-root {worktree}` and `cwd` pinned to the worktree, then the copy-from-main fallback), non-fatal and idempotent, with the verdict taken from the file on disk.
   - Whether the production happens inside `worktree-create` for every plan or only when the lane asks for it (a flag) is decided at outline and recorded with the reason. The lifecycle's phase-5 move-in must keep producing its own executor exactly as today.
   - The lane's `resolve` / setup result states `executor_in_worktree: present` or `absent` with the reason.

   *Done when:* a fixture lane worktree has a non-empty `.plan/execute-script.py` after creation; a fixture where generation fails and main's executor exists gets the copy; a fixture where neither is possible reports `absent` with its reason and does not fail the creation. A lifecycle fixture still reaches phase 5 with the move-in executor. At HEAD `worktree-create` produces no executor (HYPOTHESIS, see Claim Labels).

2. **A verb refreshes the worktree executor after the plan changes the script set, and a run never needs a direct interpreter call for it.**
   - A `git-workflow` verb regenerates the worktree's executor with the same seam and reports `executor_regenerated` and its detail. It is reachable through the executor, so the guard's R5 rule (no direct interpreter call) does not apply to it.
   - The lane text tells the run to call it after adding, removing or renaming a script verb and before running the new verb, and never to run `generate_executor.py` by path.

   *Done when:* a fixture worktree whose branch adds a script is stale before the verb and resolves the new notation after it; the lane text names the verb and a doc test asserts that no lane instruction runs `generate_executor.py` directly.

3. **The lane routes its builds through the worktree executor and keeps the in-process fallback only as the degraded case.**
   - The routed build submits the worktree's own executor when `executor_in_worktree` is `present`.
   - `executor_absent_from_worktree` stays as the recorded reason for the degraded case only.

   *Done when:* a fixture lane with a present worktree executor submits a routed build against it and records no `executor_absent_from_worktree`; the same fixture without the executor falls back and records the reason (the PLAN-LB-73 behaviour, kept).

Split guard: three deliverables, one theme (a lane worktree can run a script). It touches the git-workflow seam and the lane text; the executor generator itself is not changed.

## Claim Labels

- OBSERVED: worktree creation supplies no executor. `git-workflow.py` `cmd_worktree_create` (L2197) creates the worktree, the branch and the `.plan` links; the lifecycle produces the executor later, in `prepare_execute._generate_worktree_executor` (`prepare_execute.py` L481), at the phase-5 move-in.
- OBSERVED: the same seam is reused after a rebase: `worktree-rebase-to` refreshes a stale per-tree executor (`git-workflow.py` L1604-1660, `_run_generate_executor`).
- OBSERVED: the PLAN-LB-73 branch (PR #1843, not merged when this spec was staged) records `executor_absent_from_worktree` and runs the build in-process (`runbook-lane/SKILL.md` L400-440, `runbook_lane.py` L1368 at that branch's head). It does not materialise the executor.
- OBSERVED: the operator states that every worktree has its own `execute-script` (2026-10-20, recorded in `PLAN-LB-78`).
- OBSERVED (landings): PLAN-LB-85 could not run its new Sonar verb and the bootstrap call was refused by the guard (R5, 16:35:56Z); PLAN-LB-88 asked the operator the same question and regenerated by hand; every runbook build since PLAN-LB-78 ran with `mechanism: in_process_fallback`.
- OBSERVED: the cause is not harness-specific. `cmd_worktree_create` and the lane's routing check name no harness, and the R5 wrapper table is shared by the OpenCode guard and the Claude hook. Every observation so far is OpenCode because every runbook-lane run so far was on OpenCode; no Claude or Antigravity lane run has been observed. The guard-refusal half of the symptom needs an enforcing surface, so it shows where the guard or the hook is installed. The tests of D1 to D3 therefore must not pin one harness.
- OBSERVED (consumer finding `pm-mcp-core-m2-m4-007`, high, 2026-10-23, operator-requested): four of four runbook landings of the consumer epic (PLAN-96 #143, PLAN-95 #144, PLAN-25 #145, PLAN-26 #146) report `executor_absent_from_worktree`; the build daemon was `ready` at every preflight and unused; the learned supervisory bound (617 to 776 s) expired on a full `verify` after 3000 to 5400 passing tests, each needing a second, longer run; the worktrees of three lanes running that day hold `local`, `marshal.json`, `orchestrator` and `project-architecture` and no `execute-script.py`. Cause read there: `.plan/*` is git-ignored, so a worktree never carries the executor, and `_executor_slot.py` (`worktree_executor_path`, `executor_landed`) is the helper both producers share. This finding is evidence for this plan and adds no deliverable and no file surface (`_executor_slot.py` sits in the already declared `workflow-integration-git/scripts/`). Not re-run here.
- HYPOTHESIS: the lane's worktree is created through `worktree-create` with the derived lane name as `--plan-id`, so one change there serves the lane — confirm at `runbook-lane/SKILL.md` § 1 and `runbook_lane.py` (verify-at-outline).
- HYPOTHESIS: a generated executor in a lane worktree resolves the plan's own new script verbs, because the generator discovers bundles from `--marketplace-root {worktree}` — confirm with a fixture (verify-at-outline).
- Verify-first clause: choose between producing the executor inside `worktree-create` for every plan and only on a lane flag, and record why; confirm that the lifecycle's phase-5 move-in is unchanged by either choice.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — `cmd_worktree_create`, the new refresh verb (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/prepare_execute.py` — the shared generation seam (D1)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — worktree creation, the build routing and fallback text (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `resolve` result, the routing check (D1, D3)
- OBSERVED: `test/plan-marshall/workflow-integration-git/` (D1, D2)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` (D1, D2, D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-73 landing first (it is running, PR #1843 open; it rewrote the same lane sections and `runbook_lane.py` build-gate text, and this plan changes what its D4 decided).
- Overlaps with: PLAN-LB-73 on `runbook-lane/SKILL.md`, `runbook_lane.py` and `test_runbook_lane.py` (the gate will ask until it lands); PLAN-LB-90 on the same three lane files.
- Adjacent to: `tools-script-executor/scripts/generate_executor.py` (PLAN-LB-43 D3 and D5 change it; this plan only calls it), and PLAN-LB-89 (parked), whose test-bootstrap deliverable is a different executor write.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-92-lane-worktree-executor.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
