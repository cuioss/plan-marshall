envelope_version=1
sender_type=plan
sender_id=wait-for-comments-counts-rows
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T17:45:39Z

# Seed build timeout ceilings from observed durations, not fixed constants

component: plan-marshall:build-pyproject
category: improvement
confidence: high
source_plan: wait-for-comments-counts-rows
source_pr: 1071

## Context

Two builds died at their timeout ceilings during phase 5:

```
2026-08-01T13:44:33Z [ERROR] [PYTHON] Timeout after 330s: ./pw module-tests plan-marshall
2026-08-01T15:07:04Z [ERROR] [PYTHON] Timeout after 500s: ./pw coverage plan-marshall
```

The same plan's three slowest recorded build invocations ran **621.2s, 618.6s and 559.6s**. Both
ceilings therefore sit BELOW the normal duration of the command they bound. A healthy build is
guaranteed to be killed.

The downstream cost is not just the discarded build. Each kill surfaced as
`failure_kind=script_internal_failure, exit_code=-1`, which reads as a harness kill — the signal the
project has a standing rule about never blind-retrying. The orchestrator correctly did not
blind-retry (decision.log `2026-08-01T14:09:43Z` records a full provenance analysis), but it then had
to accept a green from a DIFFERENT `worktree_sha` on a byte-identical-content argument. That is a
weaker evidentiary position than a build that simply finished, and it was forced entirely by an
under-set constant.

## Root cause

The per-command timeout is a fixed constant, chosen independently of the observed duration
distribution for that command on this project. The adaptive-budget ratchet already exists elsewhere
(`ci checks wait --adaptive` seeds its ceiling from the persisted `ci:wait` budget) but is not
applied to build commands, even though the change-ledger already records `duration_seconds` for every
`kind=build` entry.

## Proposed action

- Seed each build command's Bash/subprocess ceiling from the persisted change-ledger durations for
  that `(notation, command)` pair — e.g. `p95 * 2`, floored at the current constant — instead of a
  fixed number.
- Distinguish `timeout` from `script_internal_error` in the plan-scoped `work.log`. Today the plan log
  records `failure_kind=script_internal_failure exit_code=-1` while only the global log carries
  `[PYTHON] Timeout after 330s`; the plan-scoped view loses the ceiling-too-low cause entirely.
- When a build is killed at its ceiling, emit the observed elapsed time and the ceiling in the same
  line, so "the build is slow" and "the ceiling is low" are separable without cross-referencing two
  log files.

## Evidence

- aspect: log_analysis — `script_duration_p95_ms: 8610.0`, `script_duration_max_ms: 621240.0`, `slowest_scripts` = 621240 / 618570 / 559590 ms, all `plan-marshall:build-pyproject:pyproject_build`.
- `script-execution-2026-08-01.log` — `[PYTHON] Timeout after 330s: ./pw module-tests plan-marshall` and `[PYTHON] Timeout after 500s: ./pw coverage plan-marshall`.
- `work.log` `13:44:35Z` / `15:07:05Z` — both recorded as `failure_kind=script_internal_failure exit_code=-1`, hiding the timeout cause from the plan-scoped view.
- `decision.log` `14:09:43Z` — the forced fallback to same-content-different-sha evidence.
