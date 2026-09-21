envelope_version=1
sender_type=plan
sender_id=plan-truth-148
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:59:21Z

# Candidate lesson: an absent verifier return was correctly recorded as non-close, not as acceptance

- source_signal: qgate / 6-finalize
- record_id: d39795
- component: pm-plugin-development:ext-self-review-plan-marshall
- resolution: rejected (same refuted premise as 20faec; the state did not recur in rounds 3-10)

## What happened

Round 1 could not issue the verifier dispatch, so it filed a `verifier_unavailable` finding recording that the round carried NO acceptance and NO answer to the stop question, and routed to loop_back. The reasoning that produced the unavailability was later refuted, but the HANDLING was right: an absent verifier return was never read as an acceptance and never as `may_close: yes`, and the non-close state was pushed into the finding store rather than living only in the decision log.

## Candidate rule

Worth keeping as a positive pattern: a missing verdict is a distinct state from a negative verdict, and both are distinct from a clean pass. Record the could-not-look state in the durable store, not only in the log, so a later reader cannot mistake silence for a pass.
