envelope_version=1
sender_type=plan
sender_id=inbox-sequence-reuse-collides-with-the-archive
epic=truthful-signals
kind=landing
created=2026-07-28T14:41:25Z

## What landed

Plan `inbox-sequence-reuse-collides-with-the-archive` (PR #1034) — the inbox
sequence allocator no longer reuses a sequence number that the archive already
holds, so a drained-and-archived message cannot be shadowed by a later message
claiming the same `{sender_id}-{NNN}` slot.

## Epic relevance

Theme fit (`truthful-signals`): a reused sequence made the queue's own naming
signal untruthful — two distinct messages could occupy one identity, and the
archive's audit record silently disagreed with the live queue.

## Residue the epic should track

Two lesson-bearing observations surfaced during this run's finalize and are
emitted as separate `candidate-lesson` messages in this same batch:

1. `default:finalize-step-simplify` carries a two-level-dispatch contract
   violation in its own step definition (classified DISPATCHED, but its Step 3
   requires a further `Task:` dispatch a leaf cannot issue). The orchestrator had
   to run the inner review dispatch from main context and mark the step done by
   hand, so this run's `finalize-step-simplify` completion is
   orchestrator-repaired, not envelope-native.

2. Review-bot completeness reported a false clean: `plan-marshall:automatic-review`
   returned `complete: true` for sourcery while `ci pr comments --pr-number 1034`
   shows sourcery-ai posted an explicit weekly-rate-limit refusal and reviewed
   nothing. Coverage on this PR is therefore narrower than the finalize signal
   claimed — a known-archetype recurrence, not a first sighting.

No open fix tasks were left behind by this plan; both items above are epic-level
follow-ups against `plan-marshall:phase-6-finalize` and
`plan-marshall:automatic-review` respectively.
