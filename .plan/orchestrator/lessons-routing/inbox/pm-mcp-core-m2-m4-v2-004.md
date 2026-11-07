envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T20:34:21Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=plan-v2-93-http-tests-annotations

# Ask the operator once per merge decision on the same HEAD

## Context

In plan-v2-93 the operator was asked four times about one decision, all at HEAD a76cb3f4: the automatic-review re-review timeout ("Merge anyway - proceed unreviewed"), the pre-merge confirmation ("Yes, merge"), the merge-gate refusal ("Record the ruling and merge"), and the barrier override ruling ("Merge anyway (record reason)"). The first answer already said: merge without CodeRabbit's review of this commit. `status.metadata` ends with a `halts` answer, a `pre-merge-consent` and a `barrier-ask-override` authorization, all on the same HEAD.

## Root cause

The automatic-review halt answer is not consumed by the pre-merge barrier as a review-barrier-gap ruling, so the barrier asks again for the same gap, and the merge confirmation and the override are separate prompts.

## Proposed action

When the operator answers a review-timeout ask with "merge anyway" at HEAD X, record it as the `review-barrier-gap` authorization for X (with the reason) so the barrier accepts it, and fold the pre-merge confirmation into that same question when the answer already says merge. Ask again only when HEAD changes.

## Evidence

- chat-history-analysis: four operator prompts for one merge decision on HEAD a76cb3f4
- status.json: halts.6-finalize.automatic-review.answer plus merge_authorizations pre-merge-consent and barrier-ask-override, same head
- dispatcher fact: merged under a recorded barrier-ask-override ruling, CodeRabbit unproven on a76cb3f4 (quota-limited)
