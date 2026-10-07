envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:03:04Z

# Candidate lesson: verifier independence is reachable, but from exactly one origin

- source_signal: qgate / 5-execute (architecture question, rule d1-gate-verifier-independence)
- record_id: 472b3a
- component: plan-marshall:phase-6-finalize
- resolution: taken_into_account — SETTLED; selected the shape deliverables 8 and 9 implemented, and rounds 3-10 exercised it successfully

## What happened

The harness constraint decides the design. A dispatched subagent is a leaf and cannot spawn further subagents, so a verifier spawned from inside the author envelope is unreachable. But a verifier dispatched from the INLINE dispatcher context — the same context that already issues the author dispatch — is reachable today with no new mechanism. On the inline branch of the Step 1b gate the author IS the dispatcher context, so the verifier must then be the dispatched party for the two roles to occupy different contexts. The verifier also cannot escalate to the operator, so it returns a verdict the dispatcher records.

## Candidate rule

Durable architectural fact worth promoting out of this plan: role independence across a dispatch boundary is available whenever the ORIGIN is the main/inline context. Before concluding "independence is unreachable in this harness", check which context would issue the second dispatch — the leaf constraint bars it from the author envelope only.
