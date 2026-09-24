envelope_version=1
sender_type=plan
sender_id=truth-147-lane-reports-green
epic=truthful-signals
kind=candidate-lesson
created=2026-09-24T08:15:17Z

title = owed architecture hint: CI-timeout standing consideration
module = plan-marshall
enrich_verb = insight
source_plan = truth-147-lane-reports-green
recurrence = 3x taken_into_account over triage ci_timeout on verify runs

The project treats CI-timeout verdicts on verify runs as a standing
consideration in plan-marshall: a deadline_exceeded timeout from the
precondition wait is re-polled to run completion and the interim timeout
findings are taken into account as moot, never triaged as build failure.
Owed call: architecture enrich insight --module plan-marshall.
