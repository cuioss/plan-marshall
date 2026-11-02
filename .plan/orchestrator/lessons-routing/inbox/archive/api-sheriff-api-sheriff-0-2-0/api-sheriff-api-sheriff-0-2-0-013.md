envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T09:32:40Z

# Candidate lesson: re-verify every cited file:line at HEAD before the code-review verifier round

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 004. Suggested route: project (API-Sheriff), keep local.

Filed as a plan-marshall candidate because it concerns the code-review author step; the plan suggested it might stay project-local.



**Signal:** Q-Gate finding 89e5a6 (6-finalize, `code-review-state`, resolved `taken_into_account`).

## What happened

The code-review verifier refused the whole round (`verdict_refused at code-review`). It checked findings F1-F13 against the code and ADR-0062 and found 12 of them held. F3 cited `DispatchStage.java:94`, which is Javadoc. The hand-built `ResilienceShape` the finding was about is at `:283`. That one wrong location was enough for the verifier to refuse the round, which cost an extra author/verifier cycle. The review closed later at 7f8135cb with `may_close=true`.

## Suggested corrective action

Before handing findings to the verifier, the review author re-reads each cited `file:line` at the reviewed HEAD and checks that the line contains the construct the finding names. This matters most after a fix commit or rebase has shifted lines. Cite the declaration line of the construct, not a nearby Javadoc reference.
