envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:17:29Z

component=plan-marshall:phase-6-finalize
category=bug
status=active

# A finalize step that re-fires after its last mark-step-done leaves a record naming the wrong head

## Context

`status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"]` reads `outcome: done`, `head_at_completion: d08dc56e8725545678582b10f409f56fad161742`, `firing_count: 5`, `display_detail: "clean at round 5; content byte-identical after rebase"`.

That record is stale. A sixth round ran at 2026-09-05T00:33Z as a delta over `c57a294c` — the commit carrying the TASK-007/008 remediation of CodeRabbit's two Major findings — and returned 2 findings, both fixed in `30b325984`. The step was never re-marked after that round.

The record is the only durable evidence a later reader has. Read literally it says the CodeRabbit remediation was never self-reviewed. The run's own `finalize-step-review-retrospective` initially reported exactly that and had to publish a correction.

## Root cause

`mark-step-done` is emitted by the step at the end of a firing, but a re-fire that happens after the orchestrator has already accepted the step's completion has no obligation to re-mark. Nothing reconciles `head_at_completion` against the head the step actually last examined, so a stale record is indistinguishable from a current one.

## Proposed action

Either (a) require every re-fire of a `mutates_source`-adjacent finalize step to re-mark with the new head and an incremented `firing_count`, enforced by the dispatcher rather than by the step; or (b) make `head_at_completion` self-validating — when the recorded head is an ancestor of the current HEAD and the step's declared surface changed in between, the record reports `stale` instead of `done`, so a reader cannot mistake it for a current verdict.

## Evidence

- aspect: logging_gap_analysis — gap `6-finalize / STEP_RECORD_CURRENCY`
- `status.json` step record: `head_at_completion=d08dc56e8`, `firing_count=5`, `prior_firings=[failed, failed, failed, done]`
- decision.log 2026-09-05T00:33:17Z — round 6 ran over `c57a294c` and returned 2 findings
- decision.log 2026-09-05T03:35:45Z — "The step RECORD says head_at_completion=d08dc56e8, firing_count=5 - and that record is stale because of MY bookkeeping error, not because the review did not happen ... I never re-marked the step after that round"
