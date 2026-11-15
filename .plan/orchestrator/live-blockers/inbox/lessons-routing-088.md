envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-11-15T18:08:01Z

# Baseline-drift recovery cannot clear a conflicting drift: nothing in the recovery rebases the branch, so the second probe repeats the first

**Severity:** high (operator grade, 2026-11-15 drain of the lessons-routing inbox)
**Bundle:** plan-marshall (`plan-marshall` execution recovery, `phase-5-execute` Step 3, `phase-2-refine` Step 3d)
**Checked at:** `34b92e0ca` (origin/main)

## What was reported

pm-mcp-core plan `plan-v2-140`: `phase-5-execute` returned `baseline_drift` (7 upstream commits, one adjacent-line conflict in `doc/adr/README.adoc`). The orchestrator re-cycled through `phase-2-refine`, which resolved the Q-Gate finding as `taken_into_account` and moved the plan on, but changed no git state. The re-entered execute returned the same `baseline_drift` a second time (two consecutive rows at 21:42:18Z and 21:46:01Z). The orchestrator rebased the feature branch by hand, outside any phase, the operator had to say "rebase prior continuing", and the change-ledger remap then could not map the old commit `27d13e15`, so a row was appended by hand.

Supporting evidence from an archived landing in this epic's sibling: `plan-lb-31-in-house-reviewer-002` records "3 consecutive baseline_drift recoveries hit the loop cap; operator authorized the merge of origin/main (65b71aa1c)", after which the loop converged.

## Ground truth at the checked commit

`marketplace/bundles/plan-marshall/skills/plan-marshall/standards/execution-recovery.md:9-32`: the recovery for `baseline_drift` with `conflict_count > 0` is to log, `set-phase 2-refine`, re-dispatch refine with the standard envelope, and re-enter execute. Line 9 names "re-cycling through phase-2-refine" the canonical absorption path, and line 30 says no input propagates the drift signal because refine's Step 3d `baseline-reconcile` already sees the upstream commits. No step in that procedure rebases or merges the branch.

`workflow-integration-git/SKILL.md:226`: `baseline-reconcile` is non-mutating on every classification: it never moves the branch ref and never merges. So refine can only JUDGE the conflict. A search of `execution-recovery.md` for `rebase`, `merge origin` and `force` finds no match relevant to this path.

`phase-2-refine/standards/refine-workflow-detail.md:260` and `:276` state the design: the probe "does NOT perform the merge", the reconcile is "deferred to the rebase steps", and "the actual `git rebase` against the new baseline happens later, in `phase-6-finalize` branch-cleanup". The same passage says phase-5 Step 3 "is strictly a 'still clean?' verification gate — it aborts on drift and does NOT merge/rebase". That is the defect: a drift WITH content conflicts makes phase-5 Step 3 abort every time, so execution never reaches the phase-6 rebase that the design leaves the reconcile to. The deferral is sound for `overlap_no_content_conflict` (phase-5 self-absorbs it, `conflict_count == 0`) and has no answer for the conflicting case.

`execution-recovery.md:34-51`: the loop is capped at 3 consecutive drift returns and then stops with `drift_loop_cap_exceeded` for manual intervention. The cap bounds the loop. It does not make a conflicting drift clearable, because each loop sees the same unchanged branch.

An earlier index row (`pm 332`) records a different baseline-drift defect (drift checked against committed files only, not pending tasks' declared files). It does not cover this one.

## What is asked

Give the conflicting-drift path an explicit step that brings the branch onto the new base after refine accepts the conflict resolution, through the `git-workflow` verbs, remapping the change ledger for the rewritten commits (`PLAN-LB-91`'s remap). Or have refine return a `rebase_required` signal the orchestrator acts on before it re-dispatches execute. A second drift return whose probe equals the first should stop with a named reason, not run again.

## Source

- `pm-mcp-core-m2-m4-v2-028`, archived verbatim at `lessons-routing/inbox/archive/pm-mcp-core-m2-m4-v2/`.
