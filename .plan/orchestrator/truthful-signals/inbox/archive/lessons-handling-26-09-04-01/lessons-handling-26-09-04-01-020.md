envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-08T05:58:27Z

component=plan-marshall:phase-6-finalize
category=improvement

Relayed from Token-Sheriff PLAN-07 (PR #715 / `8f3b8aee`). ⚠ **This is a CONFIRMING observation, not a defect report** — the two-predicate merge barrier worked as designed and caught a Major finding the findings-store gate structurally could not see. Relayed because a design whose value was demonstrated under load is worth recording as evidence for keeping it.

# Candidate lesson (process observation): the merge barrier must re-read the provider, not the store

Source: process observation from plan `test-signal-and-assertion-integrity`, PR #715.
No finding filed — this is the two-predicate merge design working as intended, offered as
a confirming observation rather than a defect.

## Observation

At the pre-merge gate the findings-store predicate reported 0 blocking findings. At the
same moment, 7 comments existed on the PR that had never been fetched into the store. The
review-completeness barrier re-reads the PROVIDER rather than the store, and it caught a
Major finding the store gate structurally could not see.

## Proposed rule

A store-derived gate can only be as complete as the last fetch into it, so it cannot
detect its own staleness: "0 blocking findings" and "0 findings fetched" are the same
observation from inside the store. A merge barrier therefore needs a second predicate that
goes back to the source of truth, and the two predicates must be independent — not two
reads of the same cache.

Concretely, this is the difference between a merge and a wrong merge: the run would have
merged clean with an unread Major finding on the PR.

## Why it is worth carrying

The epic's theme is checks that report on something other than what they claim to check. A
store gate claiming to report PR review state, while actually reporting cache contents, is
that theme in its most load-bearing position — the last gate before an irreversible action.
Worth recording as a positive pattern (independent second predicate at irreversible
boundaries), not only as a defect class.
