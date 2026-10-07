envelope_version=1
sender_type=plan
sender_id=domain-over-provision
epic=operator-ux
kind=landing
created=2026-09-02T14:28:42Z

## What landed

domain-over-provision shipped as PR #1380 (merged) — the domain detector's
zero-narrative-match branch now over-provisions instead of prompting, and
resolve-outline-skill became an N-to-1 domain selector.

```landing-facts
schema=landing-facts/1
plan_id=domain-over-provision
epic=operator-ux
pr=#1380
merge_state=merged
deliverables_total=5
deliverables_done=5
total_tokens=4616201
total_wall_seconds=66311
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done,emit-landing:done
step.create-pr.pr_number=1380
step.branch-cleanup.merge_commit=bf012b2cd81dfcf220b1fcf4f4c3982b65af7816
step.finalize-step-sync-baseline.action=noop
step.finalize-step-sync-baseline.upstream_commit_count=0
step.pre-submission-self-review.rounds=7
step.pre-submission-self-review.findings=26
step.pre-submission-self-review.firing_count=4
step.project:finalize-step-deploy-target.version=0.1.1581
```

## Residue

**PLAN-01's scope grew by operator election, not by drift.** The outline surfaced a
gap it recommended deferring — `resolve-outline-skill` resolves the outline skill from
a single `--domain` with no N→1 selector, which over-provisioning makes load-bearing.
The operator elected to absorb it, taking the plan from 4 deliverables to 5. PLAN-03
and PLAN-08 in this epic touch the same detector and `phase-1-init/SKILL.md`; both now
land on top of a wider `resolve-outline-skill` contract (`domains[]` + `domain_count`,
`resolved_from`, `competing_skills[]`) rather than the scalar `domain`.

**The plan reproduced its own target defect during its own creation.** `domain-detect`
resolved THIS plan at init with `reason=inclusion_only_resolve`, `candidates[0]`, and
`additional_candidates: [documentation, general-dev, python]`, persisting only
`plan-marshall-plugin-dev` — while the deliverables were a Python script, pytest tests
and two markdown standards. That is the strongest available evidence for the epic's
premise, observed rather than argued.

**A finalize-time producer gap, not a plan defect.** Sourcery's weekly-quota refusal
matched no registered `refusal_pattern`, so a declination was credited as
participation and filed as a `pr-comment` finding. It propagates into
`actionable_count`, `pct_resolved_as_fixed`, `escapes_total`, and the
preference-emitter's authorship-admissibility gate — four sites. Cause is `quota`, not
`size`. Carried as candidate-lesson message 001; the remedy touches
`automatic-review/standards/sourcery.md`, which is outside this epic's surface.

**Orchestrator error, corrected.** The two retrospective steps were dispatched with
`orchestrated: false` without running the item-4b.a0 detection, so their lesson
dispositions initially routed to the global store rather than this inbox. Message 001
is the compensating write; messages 002-004 were emitted correctly by
`lessons-capture`. No disposition was lost, but the epic should read 001 as a
back-fill rather than a native emission.

**Cost shape worth the epic's attention.** 6-finalize consumed 15h54m wall against
1h37m worked — 14h16m of that idle was a single operator gate (the post-merge
dirty-checkout barrier, which correctly refused a main checkout it did not author).
Seven self-review rounds account for the bulk of the phase's 2.69M dispatched tokens.
