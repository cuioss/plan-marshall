envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-28T05:46:43Z

# A late review-bot round re-fires every HEAD-bound finalize verdict: third plan of one epic in a row

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-09-token-sheriff-integration-fidelity (PR #530), candidate lesson 001. Observed with plugin and executor 0.1.2021. Recurrence of the findings routed from plan-v02-20 and plan-v02-05 (verdict inputs undeclared; a waiver the merge gate ignores).

## Observation

A late CodeRabbit round on the PR produced comments that became 5 fix tasks. Each fix commit moved HEAD, and because simplify, security-audit, functional-review and code-review bind their verdicts to HEAD, all four re-ran. Steps that declare no `verdict_inputs` fail closed on verdict currency, so any HEAD move invalidates them even when the fix touched one test file. The plan then shipped five code-review advisories unfixed on purpose, because fixing them would have re-fired every head-dependent review. The late round also cost a second settle band, a gate build and a native integration run.

## What to consider

- Declare `verdict_inputs` on the review steps so a fix outside a step's input set keeps its verdict current. This is now the third plan to pay for the missing declaration.
- Or let the bot round land before the self-review steps run, or batch bot fixes into one commit so HEAD moves once.
- Shipping advisories unfixed to avoid a re-fire is a sign the cost model is wrong: a documentation or test-only advisory should be cheap to fix.
