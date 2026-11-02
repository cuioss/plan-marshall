envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T13:55:57Z

# Candidate lesson: q_gate_validation=once with plan_without_asking=true leaves pending outline findings unconsumed (plan-marshall:plan-marshall (Q-Gate loop-back))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-40-validator-terminal-edge-protocol-rules (PR cuioss/API-Sheriff#485), source message 004.


**Source**: orchestrator observation during this run. The 3-outline Q-Gate produced 5 findings, and nothing in the pipeline consumed them.
**Probable owner**: plan-marshall:plan-marshall (phase transition / Q-Gate loop-back) / plan-marshall:phase-3-outline.

## What happened

With `q_gate_validation=once` and `plan_without_asking=true`, the single 3-outline Q-Gate pass ended with 5 pending findings: 4 warnings and 1 info. No revision round was triggered, and the pipeline was ready to go on to 4-plan with the findings unresolved. The orchestrator had to re-open 3-outline by hand to fold them in. After that, all 5 were `taken_into_account`.

## Corrective rule (candidate)

`once` should mean "run the gate once", not "ignore what it finds". Either a pending warning-severity finding after the single pass should trigger exactly one revision round before the transition, or the transition should refuse while findings are pending and name them. A silent hand-off to the next phase with pending findings is a fail-open path.
