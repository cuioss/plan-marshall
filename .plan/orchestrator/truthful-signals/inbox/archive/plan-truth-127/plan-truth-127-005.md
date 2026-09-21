envelope_version=1
sender_type=plan
sender_id=plan-truth-127
epic=truthful-signals
kind=landing
created=2026-09-13T20:23:34Z

## What landed

plan-truth-127 shipped as #1483 (merged as c38342609) — the archive closer now closes every in-progress phase instead of only the first, and a new main-anchored census verb derives the open-phase population instead of restating it.

```landing-facts
schema=landing-facts/1
plan_id=plan-truth-127
epic=truthful-signals
pr=#1483
merge_state=merged
cleanup_owed=false
deliverables_total=7
deliverables_done=6
total_tokens=3537140
total_wall_seconds=124355
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.action=merged
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-sync-baseline.upstream_commit_count=5
```

## Residue

**deliverables_done is 6 of 7, and the missing one is a grading disagreement rather than undone work.** Deliverable 1 (the in-progress-phase survey) grades `missed` on task status — TASK-001 ended `infeasible` and its replacement TASK-012 ended `blocked` — while the artefact it asked for EXISTS as finding `9b6297`, a full three-cohort census taken at finalize. The task table and the findings store give opposite answers about whether it landed, and neither points at the other. The epic should treat the deliverable as satisfied and the grading as the defect.

**The survey's own figures drifted three times and must be re-derived, never quoted.** The spec claimed 30 archived / 4 carrying an open phase; its own re-grounding measured 39/6; the live census at finalize measured 46/7 (all three cohorts `coverage: complete`, nothing unreadable). The seven affected archived records are named in `9b6297` and are deliberately LEFT UNREPAIRED per the standing operator decision — rewriting an archived status.json is the falsification this epic exists to prevent.

**Four findings carried out of the plan unfixed, each with its remedy named:**
- `939919` — `UNTOUCHED_PHASE_STATUSES` has zero executable readers; it documents an invariant that the positive `== in_progress` filter actually delivers. Vacuous-authority, squarely on-theme. Take the follow-up against the POST-fix code: `in_progress_phases` now returns a discriminated `OpenPhaseScan` and the constant still has no reader.
- `353313` — `manage-metrics generate` reported `re_entered_phases[]` EMPTY on a run that re-entered 3-outline three times and 5-execute once, every one through `set-phase`, which writes the `loop_back_reentry` marker. Same family as the already-filed `documented-invocations-...-003` (which reports it on the phase-5 path), so this run shows the gap is not phase-specific — a joint fix is likely cheaper than two.
- `ac1774` — `manage-lessons consult` is structurally unrunnable once a plan directory moves into its worktree; it reads main's slot and returns `outline_not_found`. An agent treating that as "nothing surfaced" would publish a clean Lessons Consulted section over a consult that never looked.
- `4adc50` — WITHDRAWN as `rejected`, recorded because the withdrawal is the lesson. It claimed the executor carried six orphaned script mappings (162 mapped vs 156 in source) and a regeneration would drop them; the regeneration output later read `156 marketplace + 6 local = 162`. Two populations compared as if they were one. It cost a deferred task on a hazard that did not exist.

**Review yield, and why the lopsided count is not a ranking.** CodeRabbit: 7 actionable, 7 fixed, 0 rejected — including two Majors and a Medium found INSIDE this plan's own fix for the defect class the plan exists to remove. `cuioss-review-bot` reported clean on both HEADs. That zero is not comparable: its Guide is an `issue_comment`, which the counting rule scores as meta, and the contentless filter drops a clean Guide before it becomes a finding — so in this store a clean pass and silence are indistinguishable. `sourcery-ai` refused throughout on its 7-day budget.

**Two defects in the measuring apparatus itself, from the review retrospective:** the status-summary carve-out cannot fire because it matches `body`/`message` while every stored record carries the text under the quarantined `raw_input.body`; and the round-2 Medium scored as meta purely because it arrived as a comment reply rather than an inline note.

**Declared coverage gap:** plugin-doctor ran SCOPED, so its cross-skill rule class was not gated — a counterpart skill outside the four changed directories could read green locally and red at whole-tree CI.

**Deferred, not done:** the status.json-to-metrics cross-ledger reconciliation. `PLAN-TRUTH-124` has not landed; verified by sweeping all 440 scripts for its host rather than assumed.

**Cost:** 3.54M tokens across six phases, 34h32m wall / 4h16m worked. The retrospective grades this over the `multi_module + bug_fix` error anchor (2.0M / 150min) and attributes it to run SHAPE rather than any runaway envelope (max phase share 0.29): three outline passes, two manifest re-composes, three review rounds. Note `353313` — the signal that would have explained that shape reported no re-entries at all.
