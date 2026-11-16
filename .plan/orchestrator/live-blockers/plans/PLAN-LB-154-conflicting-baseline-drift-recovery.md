# PLAN-LB-154: A conflicting baseline drift is cleared by a step that brings the branch onto the new base

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

When `phase-5-execute` returns `baseline_drift` with `conflict_count > 0`, the recovery re-cycles `phase-2-refine`, which can only judge the conflict because `baseline-reconcile` never moves the branch; the re-entered execute then returns the same drift again. The loop is bounded at 3 returns but never converges on its own, and consumers had to rebase by hand outside any phase. Give the conflicting-drift path an explicit step that brings the branch onto the new base after refine accepts the resolution, and stop a second drift return whose probe equals the first with a named reason.

## Deliverables

1. The conflicting-drift recovery in `execution-recovery.md` gains a reconcile step between refine's return and the execute re-entry: the branch is brought onto the new base through the `git-workflow` verbs, and the change ledger is remapped for the rewritten commits with the PLAN-LB-91 remap. Alternative the outline may choose: refine returns a `rebase_required` signal the orchestrator acts on before it re-dispatches execute.
   - Skills: pm-plugin-development:plugin-architecture
   - Persona: implementer
2. A drift return whose probe (divergent commits and conflict set) equals the previous return's stops with a named reason (for example `drift_unchanged`) on the first repeat, instead of running up to the 3-return cap. The counter and the comparison are stated in `execution-recovery.md`.
   - Skills: pm-plugin-development:plugin-architecture
   - Persona: implementer
3. The deferral text in `refine-workflow-detail.md` § Conflict Handling and `sync-with-main.md` states that a conflicting drift is reconciled by the new step, not deferred to phase-6 branch-cleanup, and that the non-conflicting case still self-absorbs in phase 5.
   - Skills: pm-plugin-development:plugin-architecture
   - Persona: documenter

## Standing Constraints

- A non-conflicting drift (`conflict_count == 0`) behaviour is unchanged: phase 5 self-absorbs it.
- The reconcile step never force-pushes outside the `git-workflow` branch verbs and remaps the change ledger for every rewritten commit.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.

## Claim Labels

- OBSERVED: the recovery for `baseline_drift` with `conflict_count > 0` logs, sets phase `2-refine`, re-dispatches refine with the standard envelope and re-enters execute; no step rebases or merges the branch — read at `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md` lines 5-51 (re-read at HEAD).
- OBSERVED: the loop is capped at 3 consecutive drift returns with `drift_loop_cap_exceeded` and the counter resets on any non-drift return — same file, lines 34-51.
- OBSERVED (leaf reading, not re-read): `baseline-reconcile` is non-mutating; `refine-workflow-detail.md` lines 260 and 276 defer the rebase to phase-6 branch-cleanup; `phase-5-execute/SKILL.md` line 354 forbids merge or rebase in Step 3.
- OBSERVED (consumer report, not reproduced here): plan `plan-v2-140` returned the same drift twice, the branch was rebased by hand, and the ledger remap could not map the old commit.
- HYPOTHESIS: the identical-probe comparison can use `divergent_commits` plus the conflict file set already carried in the drift TOON — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md` § trigger payload (verify-at-outline).
- Verify-first clause: the outline settles whether the reconcile step is a rebase or a merge of the base and how `PLAN-LB-91`'s remap is invoked for it, against the `git-workflow` verbs at HEAD.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/sync-with-main.md` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/plan-marshall/` — doc-contract tests for the recovery text (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none staged. PLAN-LB-153 edits `execution.md`, a different file of the same skill.
- Adjacent to: `PLAN-LB-91` (shipped; the remap) stays untouched.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-154-conflicting-baseline-drift-recovery.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
