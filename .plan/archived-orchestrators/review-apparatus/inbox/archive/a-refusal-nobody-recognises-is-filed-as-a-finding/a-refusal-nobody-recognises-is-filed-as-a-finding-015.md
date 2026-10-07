envelope_version=1
sender_type=plan
sender_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
kind=landing
created=2026-08-25T09:12:00Z

## What landed

a-refusal-nobody-recognises-is-filed-as-a-finding shipped as #1344 (merged).

```landing-facts
schema=landing-facts/1
plan_id=a-refusal-nobody-recognises-is-filed-as-a-finding
epic=review-apparatus
pr=#1344
merge_state=merged
deliverables_total=6
deliverables_done=6
total_tokens=8506434
total_wall_seconds=89883
steps=finalize-step-sync-baseline:done,project:finalize-step-lessons-housekeeping:done,pre-push-quality-gate:done,project:finalize-step-plugin-doctor:done,pre-submission-self-review:done,finalize-step-simplify:done,architecture-refresh:done,push:done,create-pr:done,project:finalize-step-era-stamp-fill:done,ci-verify:done,automatic-review:done,branch-cleanup:done,project:finalize-step-deploy-target:done,project:finalize-step-sync-plugin-cache:done,project:finalize-step-review-retrospective:done,plan-marshall:plan-retrospective:done,lessons-capture:done,finalize-step-preference-emitter:done,record-metrics:done,finalize-step-print-phase-breakdown:done
step.branch-cleanup.merge_mechanism=merge_queue
step.create-pr.pr_number=1344
step.record-metrics.any_phase_missing_end_time=false
step.pre-submission-self-review.firing_count=5
```

### Scope note on `steps`

The list carries the twenty-one steps that had recorded a terminal outcome when this
message was written. `emit-landing` (order 1000) is writing it, and `archive-plan`
(order 1100) has not run — neither can honestly report its own outcome here, so
neither is listed rather than being asserted.

### What the epic should know

The plan's stated purpose is that a refusal no recognition arm can read must be
classified as its own state rather than filed as ordinary review feedback. It ships
**inert**: `UNRECOGNISED_REFUSAL_MAX_CHARS` is `None`, so the enumerative arm never
fires and the new override is never exercised at runtime. That is deliberate and
fail-safe, but it means the shipped behaviour is verified only by tests.

Two defects found during finalize changed what the PR delivers, and both are the
epic's kind of finding:

1. The pre-merge review-completeness barrier forwarded the older `--refused-causes`
   override but never `--unrecognised-refusal-bots`, leaving the new override **inert
   at the merge gate** — the one site that renders an operator prompt.
2. `classify_bot` gated the override behind `bot in refused`, while the producer
   reports `unrecognised_refusal` and `refused_bots` **disjointly**. For the only case
   the override exists for it was unreachable, and the bot resolved `absent` — a
   reviewer that declined reported as one that stayed silent. A test asserted
   `STATE_ABSENT` on that exact input, so the suite was green *because* of the defect.

Seven pre-submission self-review rounds ran; 15 findings were filed and all resolved
`fixed`. `firing_count` reads 5 against 7 actual firings — rounds 3-5 never called
`mark-step-done`, which is itself one of the filed candidate-lessons.

Fourteen `kind: candidate-lesson` messages precede this landing (twelve from
`plan-retrospective`, two from `lessons-capture`).

### Live specimen on this PR

Of three configured reviewers, only `pr-agent` participated, and its comment was
dropped as noise (`participated_but_empty`). CodeRabbit refused on `quota`; Sourcery
refused on `size` (declared cap 150000 diff characters against a measured 2670 changed
lines). `unrecognised_refusal[]` was empty, so both refusals were recognised and
classified — zero comments filed is a true zero, not a silent one.
