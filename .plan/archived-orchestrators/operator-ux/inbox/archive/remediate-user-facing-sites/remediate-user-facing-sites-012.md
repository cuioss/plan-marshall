envelope_version=1
sender_type=plan
sender_id=remediate-user-facing-sites
epic=operator-ux
kind=landing
created=2026-09-08T13:07:52Z

## What landed

remediate-user-facing-sites shipped as #1447 (merged) — the prompt-structure, vocabulary and output-volume standards applied to the operator-facing surfaces, plus a regression smoke that locks the marketplace prompt corpus clean.

```landing-facts
schema=landing-facts/1
plan_id=remediate-user-facing-sites
epic=operator-ux
pr=#1447
merge_state=merged
deliverables_total=3
deliverables_done=3
total_tokens=9514461
total_wall_seconds=76485.0
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done,archive-plan:pending
step.branch-cleanup.action=merged
step.branch-cleanup.merge_mechanism=merge_queue
step.branch-cleanup.merge_state=merged
step.branch-cleanup.upstream_commit_count=3
step.create-pr.pr_number=1447
step.record-metrics.total_tokens=9514461
step.record-metrics.total_wall_seconds=76485.0
step.record-metrics.any_phase_missing_end_time=false
step.finalize-step-sync-baseline.action=rebased
step.finalize-step-sync-baseline.upstream_commit_count=2
loop_back_iterations=6
coderabbit_quota_waits=1
```

## Residue

**The scope this plan shipped is not the scope the spec named.** The spec listed eight to ten expected
sites; running the prompt-quality analyzer live produced 11 findings across 5 files, and only one of
those five appeared on the spec's list. Three named sites carried no structured prompts at all — sibling
plans had deleted them — but still carried prose telling an agent which options to render. The spec's own
instruction to re-derive rather than trust its counts is what made this visible.

**The bundle-split guard was breached, by operator direction.** Extending the sweep into `doc/user`
put the write population across three trees (the `plan-marshall` bundle, the `pm-plugin-development`
test tree, and the `documentation` module, which belongs to no bundle). The spec's recorded default for
scope growth was to split along bundle boundaries. The operator was told the guard was breached and
directed the plan to proceed undivided.

**No instrument covers the AsciiDoc half.** The doctor rule reads marketplace skill markdown only, the
pre-submission surfacer ships no `.adoc` detectors, and the `documentation` module resolves no build
command. Those ten pages were verified by reading alone, and no future change will be checked either.

**Follow-ups this plan deliberately did not take**, listed so the epic can schedule them:

- The prompt-quality rule is excluded from the build gate by design, so CI will not block a reintroduced
  defect. The new smoke test is the only automated guard and it covers the marketplace corpus only.
- Residual vocabulary: `micro-lane` across `doc/user/recipes.adoc` and `doc/user/configuration.adoc`;
  `Q-Gate` and `envelope` in `configuration.adoc` where they sit beside the literal config keys they name.
- Two menus exceed the four-option cap; three prompts in `provider-setup.md` offer a single option. Both
  pre-existing and outside the declared change set.
- `triage.md` offers no disposition meaning *rejected*, and `taken_into_account` routes to an insight
  hint — so a refuted finding can be recorded as a standing concern. Filed as inbox message 010.

**Cost.** 9.5M tokens against a 2.0M error threshold for this change class; `6-finalize` alone is 59% of
it. Six loop-back iterations of a 17 ceiling, four of them self-seeded — each fix round's own prose
introduced the defect the next round caught, three times in one passage. One 90-minute CodeRabbit quota
wait was served. The cost is review-loop cost, not implementation cost: phases 2 through 5 together spent
1.9M.
