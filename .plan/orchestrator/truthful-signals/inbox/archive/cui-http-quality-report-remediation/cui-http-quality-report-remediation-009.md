envelope_version=1
sender_type=orchestrator
sender_id=cui-http-quality-report-remediation
epic=truthful-signals
kind=candidate-lesson
created=2026-10-05T07:59:06Z

component=plan-marshall:phase-3-outline
category=improvement

# Deep-lane outline does not persist CERTAIN_INCLUDE assessments, so Q-Gate coverage check always fires

## Source

- Plan: plan-12-javadoc-samples-and-api-prose (PR #260)
- Signal: Q-Gate finding 6d1054 (phase 3-outline), resolved `taken_into_account`

## What happened

The outline Q-Gate ran `assessment list --certainty CERTAIN_INCLUDE` and got 0 records
(`findings_store_state: missing`) even though `planning_lane` was `deep` and the outline named
35 write-set paths over 7 deliverables. The same Q-Gate pass then independently confirmed every
path against the module inventory and content searches, so coverage was substantiated. Only the
assessment records were missing.

## Why it matters

The Q-Gate Step 2.2 coverage check assumes the deep outline lane persists one CERTAIN_INCLUDE
assessment per write-set path. When the lane skips that write, the check reports a false
"coverage missing" finding on every deep-lane plan. Someone then has to resolve it by hand, and
the coverage evidence the gate exists to check is never stored.

## Suggested correction

Either make the deep outline lane persist `assessment add --certainty CERTAIN_INCLUDE` records
for each deliverable write-set path before the Q-Gate runs, or let the Q-Gate count its own
inventory and content-search confirmation as coverage evidence when the assessment store is
`missing`. Today the gate and the lane disagree on who owns the record.

## Routing

From cui-http epic `quality-report-remediation`, PLAN-12 (cuioss/cui-http #260), inbox message `plan-12-javadoc-samples-and-api-prose-002.md`. Routed by the cui-http orchestrator on 2026-10-05.
