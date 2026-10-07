envelope_version=1
sender_type=plan
sender_id=cross-check-dated-archive-self-collision
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-10-02T09:30:14Z

component=plan-marshall:phase-6-finalize
category=improvement
created=2026-10-02
source_plan=cross-check-dated-archive-self-collision
confidence=high

# Detect a dequeued PR in the merge-queue landing gate

## Context

branch-cleanup enqueued PR #1676 and the queue-landing gate waited its full `merge_queue_wait_budget_seconds` (1800s), ending with "enqueued but not merged after 1800s (terminal observation: open)" and an F1 loop-back that consumed iteration 4 of 5. Five minutes later the orchestrator established that the PR had not been slow: the merge queue had ejected it after merge-group run 36916737805 failed 248 tests on a red base. A re-enqueue would have failed identically.

## Root cause

A PR the queue ejects returns to `open`, the same state a PR still waiting in the queue shows. The gate observes only PR state, so "ejected" and "still queued" are one observation and the only exit is the budget.

The CI abstraction offers nothing to tell them apart. At 8665ddacf `ci pr --help` lists `merge-queue` (enqueue) and `landing-state` (merged / pr_open / pushed_no_pr / unpushed); neither reports queue membership or the merge-group run result. The other verb families were not inspected. The orchestrating session reports it used `gh` directly twice (read-only) to find out; those calls are in main context and appear in no plan log.

## Proposed action

1. Add a read verb to `tools-integration-ci` that returns, for a PR, whether it is currently in the merge queue and the conclusion and id of its latest merge-group run.
2. Have the landing gate poll it and exit early with a distinct `dequeued` terminal observation carrying the failing run id.
3. Route `dequeued` to "the base is red or the PR conflicts - repair, then re-enqueue" without spending a loop-back iteration, and do not offer re-enqueue while the base is known red.

## Evidence

- work.log 2026-10-01T19:45:47Z (enqueue), 20:16:22Z (gate timeout warning), 20:16:34Z (loop-back iteration 4/5)
- decision.log 2026-10-01T20:21:35Z (dequeue established, run id, 248 failures, none in the plan's tests)
- script log: `ci` 17 calls, 2,137,710 ms cumulative; `ci_complete_precondition` 4 calls, 1,614,890 ms
- direct-gh-glab-usage aspect reported 0 over plan logs and plan diff - it cannot see main-context calls
