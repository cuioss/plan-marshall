envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:51Z

# review_support validate delta round breaks after rebase (delta base gone)

**Component (foreign):** plan-marshall:phase-6-finalize review_support (`validate`, delta/full verifier rounds)
**Category:** improvement
**Source plan:** plan-14-operator-and-question-stores

## Observation

`review_support validate` plus a dispatched verifier normally runs a delta round followed by a closing full round. After a rebase the delta base commit no longer exists on the branch, so the delta cannot be computed; the dispatcher ran the full round directly as a workaround.

## Suggested corrective action

- Detect that the recorded delta base is not an ancestor of HEAD and switch to the full round explicitly, reporting `delta_base_rewritten: true`, instead of leaving it to the dispatcher's judgement.
- Alternatively, map the delta base through the rebase (patch-id / range-diff), sharing the remap mechanism proposed for manage-change-ledger.
