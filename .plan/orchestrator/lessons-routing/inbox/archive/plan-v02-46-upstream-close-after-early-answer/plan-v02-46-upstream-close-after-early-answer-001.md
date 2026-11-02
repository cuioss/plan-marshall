envelope_version=1
sender_type=plan
sender_id=plan-v02-46-upstream-close-after-early-answer
epic=lessons-routing
kind=finding
created=2026-10-22T18:04:10Z

# Recurrence: outline criteria snapshot keeps only the first criterion line per deliverable (plan-marshall:phase-6-finalize functional review / manage-solution-outline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-46-upstream-close-after-early-answer (PR cuioss/API-Sheriff#513, merge e70743f), lessons-capture step.

Recurrence of api-sheriff-api-sheriff-0-2-0-004 ("review_support validate counts a multi-bullet success-criteria block as one criterion").

## Observation

The outline criteria snapshot (`work/criteria-snapshot.json`, built through `load_outline_deliverables`) kept only the first line of the first success-criterion bullet per deliverable. The functional-review verdict could therefore hold only one criterion row per deliverable: sealing a verdict that graded C2..Cn was refused with `unknown_criterion_id`, so every criterion after the first could not be recorded as graded.

## Why it matters

The functional review is supposed to grade every success criterion. When the snapshot collapses a multi-bullet block to one row, the remaining criteria are silently ungradeable, and the seal error points at the verdict rather than at the snapshot parser that dropped them.

## Suggested direction

Parse every bullet of the `**Success Criteria:**` block (including continuation lines) into its own criterion id in the snapshot, and add a regression test with a multi-bullet, multi-line criteria block.
