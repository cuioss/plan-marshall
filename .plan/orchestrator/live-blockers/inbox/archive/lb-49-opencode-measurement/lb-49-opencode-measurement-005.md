envelope_version=1
sender_type=plan
sender_id=lb-49-opencode-measurement
epic=live-blockers
kind=candidate-lesson
created=2026-10-22T11:23:35Z

# Pin a deliverable's consumer-visible field set before review finds it

## Context

The plan declared four deliverables and six tasks. It finished with sixteen
tasks, of which ten were review-driven fix tasks carrying `deliverable: 0`, and
a realized footprint of 25 files against 12 declared (13 realized-but-undeclared,
against a 5-file scope-creep tolerance).

Five finalize loop-backs filed them, and six of the ten fix tasks landed on one
deliverable (D2, the OpenCode normalized-token operation). Reading the titles in
sequence, each round discovered one more element of the same contract:
"measure every captured root, not only the last one",
"aggregate duplicate phase windows instead of overwriting the earlier one",
"return the documented `four_field_phases_attributed` counter",
"push the session and window filters into the queries",
"widen the millisecond window lower bound to absorb float rounding",
"clear stale enrichment-gap flags when a measured enrich write replaces them".

## Root cause

D2's contract was stated as prose against an existing consumer
(`manage-metrics enrich`), so the set of fields that consumer reads — the four
usage fields, the sub-agent totals, the run counters, the multi-root union, the
window boundary semantics — was never enumerated in one place and never pinned
by a test at outline time. Review was the first place each element was compared
against the consumer, one per round.

## Proposed action

When a deliverable serves an existing consumer unchanged (the "keep the
consumer as-is" shape), require the outline to enumerate that consumer's
consumer-visible field/edge set explicitly in the deliverable and to name one
verification criterion per element, so the review rounds verify the contract
rather than discover it. A deliverable that cannot enumerate the set is a
signal that the consumer boundary is not yet understood.

## Evidence

- aspect: request_result_alignment — 10 of 16 tasks are fix tasks (deliverable 0) from 5 loop-backs; 13 realized-but-undeclared paths; 6 fix tasks on D2
- aspect: log_analysis — `phase5_logging_gaps.outcome_pairing` 15 paired of 16, `dispatch_clustering` 7 re-entry markers
- aspect: script_failure_analysis / status.metadata — code-review fired 10 times (4 spent loop-back budget entries) and functional-review 7 times (2 loop-backs) before acceptance
- aspect: plan_efficiency — 26h09m wall, the largest single driver being repeated review rounds rather than first-pass implementation
