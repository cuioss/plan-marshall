envelope_version=1
sender_type=plan
sender_id=metrics-ledger-readers-and-timestamp-provenance
epic=truthful-signals
kind=candidate-lesson
created=2026-08-24T20:01:48Z

component=plan-marshall:manage-change-ledger
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_pr=1342

# The build oracle attributes every build to NO_PLAN and double-records each one

## Context

`analyze-logs` reported this plan's build time as:

```
build_time: { total_build_seconds: 0.0, build_count: 0, suspect_count: 0, ... }
```

In the **same fragment**, its cost rollup ranks `plan-marshall:build-pyproject:pyproject_build`
first: 77 calls, 8,201,010 ms, **58.8%** of all plan script time. A second rollup over
the folded-in global logs ranks it first again: 112 calls, 12,946,410 ms, 65.5%.

Builds demonstrably ran and dominated cost. The change-ledger — the declared build-time
ORACLE, which `plan-efficiency` is instructed to read verbatim and never re-derive —
recorded zero rows for them.

Note the reader behaved correctly. Per this plan's own shipped rule, `build_count: 0`
must render as `unavailable`, never as `0`, and it does. The defect is entirely on the
producer side.

## Root cause

Three defects, all visible in `manage-change-ledger query --kind build` (435 rows):

1. **Every build row carries `plan_id: NO_PLAN` or `null`** — never a real plan id.
   Rows written at 2026-08-23T15:57, squarely inside this plan's 5-execute window
   (13:29 Aug 23 → 07:45 Aug 24), are stamped `NO_PLAN`. A plan-scoped read therefore
   finds nothing, for every plan, always.

2. **Each build is appended twice** — once as the inner `./pw …` invocation and once
   as the outer `python3 .plan/execute-script.py …` wrapper — and the outer row
   reports `tests_run: 0` where the inner row reports the real count. One adjacent
   pair reads 769 and 0 for the same pytest run. So `build_count` double-counts, and
   whichever row a consumer reaches first decides whether tests appear to have run.
   This is the mechanism behind the separately recorded "routed build reports
   tests_run 0 on every green run" finding.

3. **No build row exists after 2026-08-23T15:57:22Z**, although builds ran through at
   least 2026-08-24T18:24 (per the plan's own `build-results/` log filenames). This is
   either a recording stop or a worktree-vs-main store split; the evidence here does
   not distinguish the two, and it is recorded as the open question it is.

## Proposed action

- Stamp the active `plan_id` on build rows; `NO_PLAN` should be the sentinel for
  genuinely plan-less builds, not the universal value.
- Append once per build, at one layer, or mark the outer row as a wrapper so
  consumers can deduplicate — and carry `tests_run` through to whichever row survives.
- Establish which store the post-15:57 builds went to, and whether a worktree-scoped
  ledger is shadowing the main one.

Until at least the first is fixed, `plan-efficiency`'s instruction to read build time
from the oracle resolves to `unavailable` on every plan, and no cross-plan build-time
trend can ever be computed.

## Evidence

- aspect log_analysis: `build_time.build_count: 0` beside `script_cost_rollup.ranked[0]`
- `manage-change-ledger query --kind build` → 435 rows, all `plan_id` `NO_PLAN`/`null`,
  last timestamp 2026-08-23T15:57:22Z
- adjacent duplicate rows with `tests_run` 769 vs 0 for the same pytest invocation
