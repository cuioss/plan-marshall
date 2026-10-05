envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T07:59:06Z

component=plan-marshall:automatic-review
category=improvement

# Candidate lesson: CodeRabbit quota refusal left required-bot participation UNPROVEN and stalled automatic-review about 1.5h

**Source signal**: automatic-review step's non-done state. Decision log 57d29a (iteration 5) and 5069ea (iteration 6) both returned escalate_ask without mark-step-done. Work log shows automatic-review completing at 21:07Z after the 19:32Z dispatch.
**Component**: plan-marshall:automatic-review (bot participation / completeness) and CodeRabbit rate limits on cuioss/cui-http.

## What happened

At head dfdc7ab, CodeRabbit refused with a quota message (19:11Z-19:26Z, "next included review in 25 minutes"). Its last review covered only 1408d91, so the required-bot participation stayed UNPROVEN (refused_awaitable). Two automatic-review rounds escalated to the operator before CodeRabbit eventually participated and the merge gate passed (participation_complete true at 21:09Z).

## Candidate rule

Quickly pushing several fix commits in the late loop-back rounds uses up the review bot's quota and then blocks the merge gate. Batch the late fixes into fewer pushes. Treat a quota refusal (refused_awaitable) as a timed wait with a known resume time, not as a question for the operator each round.

## Classification hint

Marketplace (automatic-review wait handling) plus a process note for the epic (push batching).

## Routing

From cui-http epic `quality-report-remediation`, PLAN-10 (#256); previously lesson 2026-10-04-06-009. Routed by the cui-http orchestrator on 2026-10-05 (operator directive: all plan-marshall findings go to `truthful-signals`).
