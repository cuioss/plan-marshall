envelope_version=1
sender_type=plan
sender_id=lb-14-launch-gate-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T14:55:44Z

component=plan-marshall:manage-change-ledger
category=bug

# Record daemon-routed builds in the change-ledger so build_time is measurable

## Context

For plan lb-14-launch-gate-scope the log-analysis build_time block reports `total_build_seconds: unavailable` with `ledger_present: true`, `ledger_readable: true`, `ledger_rows_scanned: 1216` and `summed_rows: 0`: the ledger holds no row for this plan. The plan script log shows 84 `pyproject_build` calls totalling 7,564,180 ms, 55 percent of all script time, and the work log shows each one resolved as `routed` with `mechanism=daemon_longpoll` through the build server. The plan-efficiency aspect therefore cannot report the plan's largest cost, and the reconciliation of the log build count against the oracle is marked unmeasured.

## Root cause

Not established from the plan artifacts. The one observable difference is that every build in this plan went through the build-server route; the working hypothesis is that the ledger row is written on the direct-execution path only. Confirm before changing code.

## Proposed action

Confirm whether routed builds write a ledger row. If they do not, write one on the routed path with the same command, duration and status fields; if they do, find why this plan's rows are missing. Either way, add a check that a plan with logged builds and an empty ledger reports the mismatch instead of only `unavailable`.

## Evidence

- aspect: log_analysis - build_time unavailable, 84 logged builds, ledger 1216 rows none for this plan
- aspect: logging_gap_analysis - BUILD_TIME_ORACLE gap
- aspect: plan_efficiency - total_build_seconds unavailable with reason
