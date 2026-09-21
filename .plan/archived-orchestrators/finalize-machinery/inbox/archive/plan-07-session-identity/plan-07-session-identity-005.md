envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-18T20:09:28Z

component=plan-marshall:manage-metrics
category=anti-pattern

# Finalize barrier probed a manage-metrics status verb that does not exist

The finalize re-review barrier path invoked `plan-marshall:manage-metrics:manage-metrics status`, but `status` is not a registered verb. The call was rejected at argparse with exit 2.

## Evidence

- Work-log entry 2026-09-18T19:24:20Z ERROR script_failure notation=plan-marshall:manage-metrics:manage-metrics exit_code=2 failure_kind=argparse_rejection detail=`status` is not a registered verb (registered verbs include accumulate-agent-usage, boundary-status, end-phase, enrich, generate, phase-boundary, print-phase-breakdown, reconcile-ledgers, record-dispatch-boundary, start-phase).
- Plan: plan-07-session-identity, PR #1530. Source signal: script-failure cluster (distinct failing notation union).
- No code fix owed in-run; the barrier proceeded under authorization and the merge completed.

## Proposed rule

Quote subcommand and flag names verbatim from the executor mapping or the script's --help output; never extrapolate a plausible verb (status/read-context/tail) from workflow prose. When in doubt, invoke the script with --help first.
