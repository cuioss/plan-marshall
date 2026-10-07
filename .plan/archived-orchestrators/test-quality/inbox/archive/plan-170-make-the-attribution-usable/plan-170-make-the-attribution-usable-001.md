envelope_version=1
sender_type=plan
sender_id=plan-170-make-the-attribution-usable
epic=test-quality
kind=landing
created=2026-09-03T02:21:09Z

## What landed

plan-170-make-the-attribution-usable shipped as #1385 (merged). The epic-surface attribution now
resolves an owning plan for 645 of 1075 modules instead of 26, and the contested set is 12 rather
than 1048 — the residual being exactly the class the derivation refuses to adjudicate, a module
claimed by two or more ACTIVE plans.

```landing-facts
schema=landing-facts/1
plan_id=plan-170-make-the-attribution-usable
epic=test-quality
pr=#1385
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=6431582
total_wall_seconds=362167
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
merge_commit=6884e932902aabb8827b0f90b9932981faada61e
contested_before=1048
contested_after=12
modules_total=1075
claimed_before=26
claimed_after=645
```

## Residue

**The derivation gained a second input source.** Plan lifecycle state — read from this epic's own
ledger `status.json` — is the first input to the partition that is not the spec corpus. The epic now
has a machine consumer of its per-plan `status` field, so a status vocabulary change (a new value
beyond landed/shipped/staged/running/parked) will raise `unknown_plan_status` rather than being
absorbed. That coupling did not exist before this plan.

**The 12 survivors are a standing decision, not a backlog item.** Lifecycle narrows the competing set
and deliberately never picks a winner among live plans. The three surviving patterns are
PLAN-155+PLAN-165 (10 modules, retired PLAN-060), PLAN-150+PLAN-160 (1, retired PLAN-070), and
PLAN-155+PLAN-160 (1, retired PLAN-060+PLAN-090). Resolving those is a scheduling question for the
epic, not a derivation defect.

**PLAN-110 is now detected as a sweep.** The broadened own-words sweep declaration reads its
"crosses several reduction slices deliberately" statement, so the sweep set is PLAN-110, PLAN-130,
PLAN-135 rather than the previous two. Any epic reasoning that assumed exactly two sweeps is stale.

**Lesson 2026-08-25-09-016 was re-examined and deliberately retained.** Its evidence cites the
multiply-claimed figure this plan changed, but the plan touched
`plan-orchestrator/templates/plan-spec.md` only — not the queue renderer or the disjointness gate it
guards. The guarded fail-open (absence from `file_overlap_matches[]` read as disjointness) stands
unfixed.

**A producer-gap the run could not mechanise.** Lesson `2026-09-02-15-001`, filed by this plan's own
phase-4, was written with no `key=value` header block at all — `list` showed it active while every
id-addressed verb returned `not_found`, so it was unreachable by `consult`. Repaired by hand this
run. Whatever wrote it produced a lesson the corpus could enumerate but not address.

**Five lessons now carry repeat observations** (`2026-08-25-09-002`, `-007`, `-009`,
`2026-09-02-13-001`, `-13-002`), two of them recording that a housekeeping run reviewed and retained
them one day before the defect they describe recurred. Retention is not an application mechanism —
nothing downstream converts a repeatedly-retained lesson into work. That is an epic-level scheduling
gap, not a finalize-step one.

**Reviewer asymmetry worth carrying forward.** CodeRabbit produced both actionable findings on this
PR, and by project default it is an OPTIONAL bot whose silence would not block a merge; pr-agent,
the sole default-required bot, participated twice and found nothing. This run overrode the lists
plan-locally. Also: Sourcery refused structurally on a stated cap of 150000 diff *characters* against
a measured 4906 changed *lines* — units that do not compare, and taken at face value a refusal firing
two orders of magnitude early.
