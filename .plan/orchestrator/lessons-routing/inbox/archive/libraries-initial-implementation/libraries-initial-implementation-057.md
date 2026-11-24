envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:36Z

component=plan-marshall:manage-metrics
category=bug
title=a re-entered 5-execute reports its whole window as idle: backfill worked duration from the dispatch boundaries
source_lesson=2026-11-23-12-003
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-23

# a re-entered 5-execute reports its whole window as idle: backfill worked duration from the dispatch boundaries

# Candidate lesson: a re-entered 5-execute reports its whole window as idle

- Source signal: plan-retrospective of plan-23-forms-hardening (inbox plan-23-forms-hardening-011; plan_efficiency and log_analysis aspects).

## What happened

`metrics.md` shows 5-execute with Worked `-`, Reported (wall) 3h19m and Idle 3h19m, while the same phase has 6 dispatch-boundary rows whose `duration_ms` sum to 8,541,329 ms (about 2h22m), and its `total_tokens` (273,114) is far below the dispatch-boundary total (2,048,047) that won the reconciliation. The phase was re-entered three times (two budget_yield envelopes, a verification hand-back, a finalize loop-back).

## Candidate rule

Worked duration is accumulated per dispatch, or backfilled from the dispatch-boundary `duration_ms` of a re-entered phase as the tokens already are, and Idle is marked unmeasured when Worked is unrecorded, so execute effort is not reported as 3h19m of idle time. Owning component: `plan-marshall:manage-metrics`.
