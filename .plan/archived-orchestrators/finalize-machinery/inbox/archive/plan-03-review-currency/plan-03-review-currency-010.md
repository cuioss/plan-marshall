envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T19:29:36Z

component=plan-marshall:plan-marshall
category=improvement
created=2026-09-17
bundle=plan-marshall

# verification-feedback loop_back returns must carry loop_back_target

The wait-region unified triage (producer=finalize-feedback) returns
`status: loop_back` without a `loop_back_target` field, and item 7c produces
no `phase_steps` record — so neither of the two surfaces the continuation
hook reads carries the granularity decision. The orchestrator had to infer
`5-execute` from `fix_tasks_created > 0` via the granularity invariant.

## Proposal

Require `loop_back_target` on every `verification-feedback` `loop_back`
return, the same validation the `mark-step-done --loop-back-target` contract
already enforces for step records. The inference is correct today and
unnecessary.

## Evidence

Plan plan-03-review-currency, unified triage return: `status: loop_back`,
6 findings triaged, 5 fix tasks, no `loop_back_target` key present.
