envelope_version=1
sender_type=plan
sender_id=truth-161-adr-number-allocation
epic=truthful-signals
kind=candidate-lesson
created=2026-09-22T22:15:17Z

envelope_version=1
sender_type=plan
sender_id=truth-161-adr-number-allocation
epic=truthful-signals
kind=candidate-lesson
created=2026-09-22T22:14:53Z

title=CI-wait timeout triage records taken into account as external-infra noise
component=plan-marshall:phase-6-finalize
category=improvement
created=2026-09-22
bundle=plan-marshall

# CI-wait timeout triage records taken into account as external-infra noise

During finalize, CI-wait timeout findings recurred and were taken into
account as external-infrastructure noise rather than plan defects, with
a verify re-run as the remedy.

## Generalized hint

Owed `architecture enrich` call: `architecture enrich insight
--module plan-marshall` — treat CI-wait timeout triage records as
external-infrastructure noise distinct from plan defects; record them
as taken into account with an infra-flake note and remedy by
re-running the verify build, rather than letting timeout records
dilute defect triage.

## Impact

Keeps timeout noise from diluting defect triage in plans with
remote-CI waits.
