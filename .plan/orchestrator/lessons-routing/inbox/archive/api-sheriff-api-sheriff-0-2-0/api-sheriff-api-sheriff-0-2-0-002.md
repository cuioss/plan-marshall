envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T15:35:21Z

# Candidate lesson: Sibling plans with overlapping files: the second to merge pays rebase cost and can lose outline criteria (plan-marshall:plan-orchestrator)

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-28-validator-limit-rules` (PR cuioss/API-Sheriff#467), source message 002.


## What happened

While PR #467 (V02-28, extract LimitRules from ConfigValidator) waited on review, sibling plan PR #465 (V02-24) landed and rewrote the same files: ConfigValidator, RuleSupport, ConfigValidatorTest and both docs. The result was 5 content conflicts. The operator chose rebase and resolve. #465 also deleted effectiveAuth, effectiveProfile and resolveAnchor, so one success criterion in this plan's outline became moot.

The epic spec's concurrency rule anticipated this ("whichever merges second rebases"), so nothing broke, but the cost was real: conflict resolution, a re-verify, and a success criterion that no longer applied.

## Lesson

When two staged plans in one epic share a footprint, the orchestrator already knows that at staging time. It should:

- flag the overlap explicitly in both specs (file list, not only the generic concurrency rule),
- prefer sequencing the two plans (or a wait-for dependency) over running them in parallel when the overlap covers the core files,
- tell the second plan to re-check its outline success criteria against the first plan's landing before finalize, so a criterion removed by a sibling is recorded as moot with a reason instead of found during review.

## Impact

Parallel plans on the same files turn a simple refactor into a rebase plus re-grading exercise late in finalize.
