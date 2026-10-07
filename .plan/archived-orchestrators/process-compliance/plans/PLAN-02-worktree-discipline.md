# PLAN-02: Worktree discipline — materialization, boundaries, hand-off gate

epic: process-compliance
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-02-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Make work-on-main with an unmaterialized worktree structurally refused: persist a
`worktree_materialized` flag in `prepare_execute`, refuse every phase-5 dispatch and
Bucket-B invocation with `use_worktree=true` while unset, extend the post-refine
main-clean assertion to every phase boundary, and add a hand-off admission gate plus
a session-start tree check before the first edit.

## Deliverables

1. `worktree_materialized` flag persisted by `prepare_execute` (`plan-marshall:workflow-integration-git:prepare_execute`) and refused by phase-5 dispatch / Bucket-B invocations while unset.
2. Main-clean assertion extended to the missing boundary 1→2 (post-1-init post-dispatch assertion mirroring the existing 2-refine/3-outline/4-plan trio); audit 5-entry worktree-resolution coverage, extend only if absent.
3. Hand-off admission gate (plan record + `feature/` branch + worktree + proven-clean main) and session-start tree check before the first repo edit.
4. Regression tests for each refusal; docs naming the residual (no script gate binds a free agent's Edit tool — paired with detection).

## Claim Labels

- OBSERVED: Work on main with use_worktree=true and never-materialized worktree occurred twice from independent sessions — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material C`
  - verdict: corroborated | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic Inherited Material C records work-on-main with never-materialized worktree from two independent sessions
- OBSERVED: Post-dispatch clean-main assertions exist at three boundaries — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` § `Post-dispatch contract assertion` (2-refine) and `planning-outline.md` §§ `Post-dispatch contract assertion` (3-outline, 4-plan); the 1→2 boundary has none (re-scoped 2026-09-18 after refutation of the one-boundary premise)
  - verdict: contradicted | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: yes | evidence: Absorbed: claim re-authored to the three real assertion sites; deliverable 2 narrowed to the missing 1-2 boundary; surface now declares planning.md, planning-outline.md, prepare_execute.py
- HYPOTHESIS: `prepare_execute` is the seam that persists execution prep where the flag belongs — confirm/refute at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/prepare_execute.py` § `run_prepare_execute` (verify-at-outline; re-scoped 2026-09-18: not phase_handshake.py)
  - verdict: contradicted | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: yes | evidence: Absorbed: claim re-pointed at workflow-integration-git/scripts/prepare_execute.py run_prepare_execute; surface updated in the same act
- HYPOTHESIS: Phase-5 dispatch fans out through execute-task injection paths that can read the flag — confirm/refute at `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py` § `inject_project_dir` (verify-at-outline)
  - verdict: corroborated | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: inject_project_dir defined at inject_project_dir.py:82 with subcommand dispatch at :208; no bare inject symbol, claim text corrected
- Verify-first clause: The consuming phase must settle both HYPOTHESES against the implementing source before scoping — refutation loops back to re-scope. Stated residual rides along: no script gate binds a free agent's Edit tool.
  - verdict: unverifiable | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/prepare_execute.py` — move-in seam owning the flag
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py` — dispatch guard reader (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning.md` — post-refine clean-main assertion docs
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/planning-outline.md` — outline/plan clean-main assertion docs
- OBSERVED: `test/plan-marshall/phase-5-execute/` — regression tests for the guards

## Dependencies and Sequencing

- Depends on: PLAN-01 (gate vocabulary settled first; no file overlap, ordering only)
- Overlaps with: PLAN-05, PLAN-06 on `execute-task/scripts/inject_project_dir.py` (sequenced under scope=1; corrected 2026-09-18 — was wrongly "none")
- Adjacent to: WS-01 transition gate — adjacent boundary, separate files

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/process-compliance/plans/PLAN-02-worktree-discipline.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Re-grounding instruction

Re-verify every Claim Label against the implementing source at HEAD during outline;
settle each HYPOTHESIS via `corpus set-verdict` before scoping. Do not proceed on a
refuted premise.

## Adjacency and overlap notes

If `prepare_execute` is not the correct seam, re-scope to the actual prep seam and
record the correction in the inbox message. Never gate the free agent's Edit tool
directly — refuse at dispatch/invocation seams and pair with detection.

## Incorporated lessons

- `archive/lessons/2026-08-25-09-015.md` — session-restart cwd re-pin (diagnostic +
  structural); the hand-off/session-start checks close the same hole.
- `archive/lessons/2026-09-17-19-001.md` — single-location assertion after move-in:
  doubled `.plan/local` segments are expected nesting, never duplication evidence.

## Folded inbox evidence (drain 2026-09-18, no new file surface)

- `git-branch-mechanics-001` item 3: orchestrator dispatched execute with
  `WORKTREE: .` on a `not_yet_materialized` plan, bypassing `prepare_execute` +
  cwd-pin and recreating a `references.json` stub on main. Carry into the
  hand-off admission gate as a hard precondition candidate: pre-dispatch
  `get-worktree-path` state (`pending` vs materialized) must gate the execute
  dispatch. Enforced inside the already-declared dispatch-guard seam; no new
  surface.
- `plan-07-session-identity-001` V1: unowned PLAN-07 implementation dirt on main
  (4 modified + 1 untracked), remediated via `git stash push -u`; residual (stash
  applies only inside the phase-5 worktree, never on main) is exactly the
  hand-off-gate + session-start-check behavior this spec stages.
- `plan-07-session-identity-002` Causes 1+3: curiosity outran lifecycle entry
  (investigation before init → no plan_id, no phase, no worktree owner) and
  establishment-IS-the-control (placement rules only constrain entered
  lifecycles). Corroborates the admission-gate ordering: identity before
  investigation.
