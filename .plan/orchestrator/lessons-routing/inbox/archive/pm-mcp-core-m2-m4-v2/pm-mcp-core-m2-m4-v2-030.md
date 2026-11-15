envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-13T13:17:31Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall

# Re-run the reviews right after a review-prompted correction commit, not at the merge barrier

- component: plan-marshall:phase-6-finalize
- category: improvement
- confidence: high

## Context

In plan-v2-140, code-review and functional-review recorded their verdicts at HEAD 74b3f665. Their advisories prompted a documentation-correction commit (c76e5b3e), and finalize then went on through push, create-pr, ci-verify, automatic-review and sonar-roundtrip. Only at branch-cleanup did the pre-merge HEAD binding refuse the merge (`merge_candidate_not_gated`: both reviews were ungated at c76e5b3e). Both reviews were re-run and branch-cleanup was re-entered. The barrier worked, but the stale review state went unnoticed through five steps, and the second round surfaced two more advisories that were then left unfixed "to end the correct-and-re-review cycle".

## Root cause

A correction commit made in response to review findings does not invalidate the review steps' `head_at_completion` at the time of the commit. The mismatch is detected only by the pre-merge barrier.

## Proposed action

When finalize commits a fix for review findings, invalidate the review steps whose `head_at_completion` no longer matches HEAD, and re-run them before push. Or treat a review-prompted fix commit as a loop-back into the review pair. State a convergence rule (for example, advisory-only second round closes) so the loop ends on purpose rather than by an ad-hoc decision.

## Evidence

- decision.log 2026-11-13T09:39:43Z [WARNING] 469bef: "merge_candidate_not_gated — candidate c76e5b3e, ungated steps code-review and functional-review (recorded at 74b3f665, before the documentation-correction commit c76e5b3e that those reviews themselves prompted)"
- status.json phase_steps: code-review firing_count 2, functional-review firing_count 2
- decision.log 09:41:41Z 94f77f: advisory "Left as is to end the correct-and-re-review cycle"
- chat history loop_back: 6-finalize pre-merge HEAD barrier
