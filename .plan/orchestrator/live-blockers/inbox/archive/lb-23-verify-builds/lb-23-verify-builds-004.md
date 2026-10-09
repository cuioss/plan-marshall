envelope_version=1
sender_type=plan
sender_id=lb-23-verify-builds
epic=live-blockers
kind=candidate-lesson
created=2026-10-09T10:01:50Z

component=plan-marshall:execute-task
category=improvement
created=2026-10-09
bundle=plan-marshall
source_plan=lb-23-verify-builds
confidence=high

# Route per-task tests to a directory scope when module-tests exceeds a leaf

## Context

On plan lb-23-verify-builds, 14 of the first 16 tasks sat in the `plan-marshall` module, whose `module-tests` resolved to the orchestrator tier (1307 s at first, bound above the Bash ceiling). The first execute dispatch yielded on TASK-1 with nothing done. The operator chose to run the tests once per batch. Every executing leaf then reported that no test it wrote had been run, and three failures surfaced only at the batch runs: a class-scoped fixture declared as an instance method (TASK-17), a forwarded-signal defect in `_run_bounded` (TASK-18, a production bug), and a missing `allow_daemon_routing` marker (TASK-19). 5 of 7 execute dispatches ended `voluntary_checkpoint`.

## Root cause

The task verification command is module-scoped, and `resolve-test-scope` returned `recommended_target: null`, so the leaf saw no smaller runnable unit. A smaller unit exists: in the last execute round the leaf ran directory-scoped `module-tests plan-marshall/build-server` (500 tests), `plan-marshall/manage-architecture` (744) and `plan-marshall/phase-6-finalize` (1337) synchronously in 15 to 32 seconds each. `test-compile` as a task verification does not catch a fixture error.

## Proposed action

- When the module-scoped test command resolves to the orchestrator tier, have `execute-task` fall back to the directory (or file) scope of the tests the task touched, run that inline, and defer only the module-wide run.
- Make `architecture resolve` able to return a tier verdict for a sub-directory test scope, so the fallback is resolved rather than improvised (the leaf noted "the directory-scoped test runs have no tier verdict of their own").
- Until then, state in the task contract that a "must be observed failing before the source change" criterion cannot be met under batched tests: it was unmet on deliverables 1, 2, 3, 4 and 6 of this plan.

## Evidence

- aspect: logging_gap_analysis - 5-execute dispatch causes: 5 voluntary_checkpoint, 1 budget_yield, 1 clean_exit_queue_empty.
- aspect: chat_history_analysis - "resolve-test-scope returned recommended_target: null, divergence_possible: true"; "module-tests plan-marshall/build-server: 500 tests, success".
- aspect: request_result_alignment - 7 of 23 tasks are fix tasks, 3 of them from batch test failures.
- A whole-tree `module-tests` run resolved per_task at 462 s, timed out at 433 s without a verdict, and doubled the learned bound; `verify plan-marshall` resolved per_task at 376 s while embedding the suite that resolves orchestrator tier at 1307 s.
