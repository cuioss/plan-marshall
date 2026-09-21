envelope_version=1
sender_type=plan
sender_id=apply-the-cloud-plan-lane-contract-amendments
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T06:17:56Z

component=plan-marshall:phase-6-finalize
category=improvement
status=active

# Finalize dispatch boundaries stamp step_complete even when the step returned findings

## Context

All 8 recorded rows in `work/metrics-dispatch-boundaries-6-finalize.toon` carry `termination_cause=step_complete`. None carries `returned_with_findings`. Yet `pre-submission-self-review` returned findings in rounds 1, 2, 3, 4 and 6 on this plan — five findings-bearing terminations recorded as clean completions.

## Root cause

`returned_with_findings` exists precisely to mark a productive non-completion, and the logging-gap contract excludes it from the agent-initiated-re-dispatch >50% threshold for exactly that reason ("a high `returned_with_findings` share means the review dispatches were doing their job"). Because the finalize dispatcher never stamps it, the exclusion has nothing to exclude and the boundary record cannot distinguish a clean step from a findings-bearing one.

The consequence is not cosmetic: `error_total_tokens` vs `retryable_total_tokens` vs productive-loop-back spend are the three cost classes the retrospective is supposed to separate, and one of the three is invisible on every finalize run.

## Proposed action

Have the finalize dispatcher stamp `returned_with_findings` when the step's return payload carries a non-empty findings list, and reserve `step_complete` for a clean return. This is a one-branch change at the `record-dispatch-boundary` call site, not a new mechanism.

## Evidence

- aspect: logging_gap_analysis — `dispatch_termination_by_phase` 6-finalize: 8 rows, "8 step_complete, 0 returned_with_findings"
- decision.log records findings-bearing self-review returns at 15:16Z (123 candidates), 15:22Z, 15:34Z, 15:54Z (round 4, 2 findings) and 00:33Z (round 6, 2 findings)
- `manage-findings qgate list` → 5 persisted findings from those rounds
- Contrast: 5-execute correctly stamps `voluntary_checkpoint` (3) and `clean_exit_queue_empty` (2), so the vocabulary is in use elsewhere
