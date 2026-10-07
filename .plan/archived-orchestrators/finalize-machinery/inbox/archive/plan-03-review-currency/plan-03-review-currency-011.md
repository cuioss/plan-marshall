envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T19:29:45Z

component=plan-marshall:plan-marshall
category=improvement
created=2026-09-17
bundle=plan-marshall

# verification-feedback producer vocabulary is inconsistently enforced

A triage dispatch with `producer=ci-verify-timeout` succeeded once (4
findings accepted, no fix tasks) and was later rejected with
`contract_violation` listing six allowed producers plus the remedy to use
`finalize-feedback`. Same input shape, opposite verdicts.

## Proposal

Do one of the two, not both across runs: either accept `ci-verify-timeout`
as an alias that routes to the documented owner for triage-type CI-timeout
findings, or reject it consistently and document which producer owns those
findings (the rejection remedy named `finalize-feedback` / `pr-state` —
name the owner in the workflow doc, not only in the error).

## Evidence

Plan plan-03-review-currency: first ci-timeout triage with
`producer=ci-verify-timeout` returned success; second identical-shape call
returned `contract_violation` with allowed producers
[build-runner, sonar, pr-comment, plugin-doctor, pr-state,
finalize-feedback].
