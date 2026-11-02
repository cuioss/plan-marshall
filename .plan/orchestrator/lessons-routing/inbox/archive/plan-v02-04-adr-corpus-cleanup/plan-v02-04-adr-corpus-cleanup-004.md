envelope_version=1
sender_type=plan
sender_id=plan-v02-04-adr-corpus-cleanup
epic=lessons-routing
kind=finding
created=2026-10-26T09:55:56Z

# Recurrence: a baseline-drift rebase forces every review step to re-fire, even when the replayed commits are byte-identical (plan-marshall:phase-6-finalize verdict currency)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-04-adr-corpus-cleanup (PR cuioss/API-Sheriff#521, merge f5826465), lessons-capture step.

Related to `lessons-routing-005` ("Head-dependent finalize steps re-fire in full") and `lessons-routing-001`.

## Observation

`main` moved (PR #520, 6b8d88f4) during finalize, and the branch was rebased onto it. The plan's own commits replayed with no content change, but their SHAs changed. Every head-dependent step (simplify, security-audit, functional review, code review, pre-push gate, and the wait region) re-fired because its `head_at_completion` no longer matched HEAD. Final firing counts: functional-review 7, simplify 5, code-review 4, security-audit 4.

## Why it matters

A rebase over unrelated upstream commits changes nothing the reviews judged. Re-firing them costs full review rounds (and verifier dispatches) and adds nothing.

## Suggested direction

Classify verdict currency by the plan's own diff (patch-id or the tree diff of the plan's changed paths against the new base), not by the HEAD SHA. A rebase whose replayed patches are patch-id-identical and whose upstream delta does not intersect the plan footprint should keep the recorded verdicts current.
