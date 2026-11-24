envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:11Z

component=plan-marshall:manage-metrics
category=improvement
title=record-dispatch-boundary has no termination cause for an external rate-window wait
source_lesson=2026-11-18-13-009
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-18

# record-dispatch-boundary has no termination cause for an external rate-window wait

# Candidate lesson: record-dispatch-boundary has no termination cause for an external rate-window wait

- Source signal: plan-retrospective, plan git-core-import (inbox git-core-import-011).

## What happened

The automatic-review dispatch at 2026-11-18T12:35:53Z returned `escalate_ask` with reason `rate_window_await` (CodeRabbit's quota window armed for 56 minutes). Its dispatch-boundary row carries `termination_cause: blocked_session_restart` (118077 tokens), so the retrospective counts a bot-quota wait as a session-restart retryable spend. Nothing restarted.

## Root cause

`DISPATCH_TERMINATION_CAUSES` has no value for an external rate-window wait, so the recorder picks the nearest retryable bucket and the cause stops saying what happened. The same mislabelling shows in plan-18-leftover-fixes (two `blocked_session_restart` rows, 247031 retryable tokens, caused by the close-and-reopen recovery).

## Candidate rule

Add a cause such as `rate_window_await` to `DISPATCH_TERMINATION_CAUSES`, keep it in the retryable class, have the automatic-review escalate path record it, and update the logging-gap-analysis cause list to match.


## Related case in a later plan (implement-plan-06-build-guards, inbox implement-plan-06-build-guards-013)

- Source signal: plan-retrospective (log-analysis, plan-efficiency, logging-gap-analysis `DISPATCH_TERMINATION_CAUSE`), component `plan-marshall:phase-5-execute`, confidence high.
- The 5-execute envelope that ran TASK-8 returned `status: infeasible` with a verified reason (GraalVM's `resource-config.json` must be a top-level object). Its dispatch boundary was recorded with `termination_cause: error` at 195,152 tokens, so the log analysis reports `error_total_tokens: 195152` for 5-execute, spend the logging-gap contract defines as "genuinely non-productive: raised a fatal error and returned nothing", although the dispatch returned a real format finding.

Same gap, second case: the closed `--termination-cause` set has no cause for a leaf that stopped on purpose and handed a decision back (here an `infeasible` return, above an external rate-window wait). Map an `infeasible` return to an existing hand-back cause (for example `blocked_user_review`) or add a dedicated cause, so the `error` figure keeps meaning terminal waste. See also lesson `2026-11-19-14-001` (a free word such as `completed` is rejected): the recording step should map each envelope return to the enum through a table.
