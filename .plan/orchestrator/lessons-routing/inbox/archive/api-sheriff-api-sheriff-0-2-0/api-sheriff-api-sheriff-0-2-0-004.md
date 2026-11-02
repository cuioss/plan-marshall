envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T15:35:22Z

# Candidate lesson: review_support validate counts a multi-bullet success-criteria block as one criterion (plan-marshall:phase-6-finalize)

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-28-validator-limit-rules` (PR cuioss/API-Sheriff#467), source message 004.


## What happened

Deliverable 1 of this plan's solution outline listed 5 success-criteria bullets. `review_support validate` parsed them as a single criterion. Because the validator expects one verdict row per parsed criterion, the functional-review verdict had to merge all 5 bullets into one row to pass validation.

## Lesson

The success-criteria parser in review_support should split the criteria block into one criterion per bullet, the same way the outline author writes them. Until it does, the verdict loses per-criterion grading: one row cannot say that four bullets are met and one has a residual.

## Expected fix

- Parse each top-level bullet under the success-criteria heading as its own criterion.
- Add a test with a multi-bullet criteria block (for example 5 bullets) that asserts 5 criteria are parsed.
- Report the parsed count in the validate output, so a count mismatch shows up instead of being absorbed.

## Impact

Coarser review verdicts and verdict rows shaped by the parser instead of by the outline.
