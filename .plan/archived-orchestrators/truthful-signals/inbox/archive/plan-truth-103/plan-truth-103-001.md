envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:00:36Z

# Change-ledger build oracle records nothing since 2026-09-07

component: plan-marshall:manage-change-ledger
category: bug
confidence: high
source_plan: plan-truth-103
source_aspects: log_analysis, logging_gap_analysis, plan_efficiency

## Context

`analyze-logs.py::summarize_build_ledger` reads the append-only change-ledger at
`.plan/work/change-ledger.jsonl` and documents it as "the build-time ORACLE ...
spans EVERY build system and EVERY phase". For plan-truth-103 it returned
`build_count: 0`, `total_build_seconds: 0.0`, and an all-zero status partition.

Measured first-party during this retrospective:

- `manage-change-ledger query --kind build` returns 456 rows. The **last** one is
  dated `2026-09-07T20:55:15Z`.
- `manage-change-ledger query --kind job` returns 46 rows. The **last** one is
  dated `2026-09-07T13:25:08Z`.
- plan-truth-103 ran 2026-09-12 to 2026-09-13 and made **42** `pyproject_build`
  calls inside its own script log (3,339,840 ms — 39.5% of all plan script time)
  plus **83** in its folded-in global logs (15,673,970 ms — 70.8%).

Not one of those ~125 build invocations produced a ledger row. Neither did any
build by any other plan on this machine in the six days since 2026-09-07.

## Root cause

Unknown at the write side — this retrospective measured the absence, not its
mechanism. The two candidates worth checking first: the ledger is resolved at
`.plan/work/` (the tracked-config tree), so a build executing with a
worktree-relative cwd may be writing to a ledger inside the worktree that is
destroyed with it; or the `classify-outcome` / append call site stopped being
reached when the build daemon path became the default. The 2026-09-07 cutoff is
a sharp edge, not a decay, so a single change is the likely cause.

## Why it stayed invisible

`references/log-analysis.md` instructs the reader that `build_count: 0` means
"build time UNAVAILABLE (absent is not zero)", and `plan-efficiency.md` requires
rendering it as `unavailable` rather than `0`. Both rules are correct and both
were followed. The consequence is that a **dead oracle and a plan that genuinely
never built are the same observation**, so a six-day total outage of the only
build-time measurement in the system produced no alarm anywhere — including in
the retrospective aspect whose entire job is to report build time.

This is the epic's archetype in an unusually pure form: the honest-absent
discriminator is present and working, and it is precisely what absorbs the
signal.

## Proposed action

1. Find and fix the write side (bisect from 2026-09-07 on the ledger append call
   path and the worktree cwd resolution of `.plan/work/`).
2. Add a **staleness** signal the read side can publish: `summarize_build_ledger`
   already knows the plan's own execution window, so a `build_count: 0` over a
   window in which the plan's script log shows build invocations is a
   distinguishable third state — not "no builds ran", not "unavailable", but
   "the oracle did not record builds we can prove happened". That state should
   be an `error` finding, not an absent figure.

## Evidence

- aspect: log_analysis — `build_time: {total_build_seconds: 0.0, build_count: 0, suspect_count: 0, pass: 0, error: 0, timeout: 0, killed: 0, status_unknown: 0}`
- aspect: log_analysis — `script_cost_rollup.ranked[0]: plan-marshall:build-pyproject:pyproject_build, 42 calls, 3339840.0 ms, 39.452%`
- aspect: log_analysis — `global_log_signals.cost_rollup.ranked[0]: pyproject_build, 83 calls, 15673970.0 ms, 70.84%`
- first-party: `manage-change-ledger query --kind build` last row `2026-09-07T20:55:15Z`; `--kind job` last row `2026-09-07T13:25:08Z`
- source: `analyze-logs.py::summarize_build_ledger` filters `entry.get('kind') != 'build' or entry.get('plan_id') != plan_key`
