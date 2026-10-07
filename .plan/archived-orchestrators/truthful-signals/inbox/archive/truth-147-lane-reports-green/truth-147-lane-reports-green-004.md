envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=truthful-signals
kind=candidate-lesson
created=2026-09-24T08:15:36Z

title = owed architecture hint: review-bot wait timeout standing consideration
module = plan-marshall
enrich_verb = insight
source_plan = truth-147-lane-reports-green
recurrence = 2x taken_into_account over triage ci_timeout on review-bot waits

The project treats review-bot wait timeouts as a standing consideration
in plan-marshall: a deadline_exceeded CodeRabbit wait is re-polled to
run completion and the interim timeout findings are taken into account
as moot, never triaged as review failure.
Owed call: architecture enrich insight --module plan-marshall.
