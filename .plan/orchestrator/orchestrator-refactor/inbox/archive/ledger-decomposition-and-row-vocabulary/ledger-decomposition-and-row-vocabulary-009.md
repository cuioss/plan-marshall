envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=orchestrator-refactor
kind=candidate-lesson
created=2026-09-24T09:05:30Z

# Match xdist_group nodeid suffixes in assert_test_identifiers

component: plan-marshall:execute-task
category: bug

## Context

In ledger-decomposition-and-row-vocabulary, TASK-17's diff assertion reported 1 missing identifier: `test_orchestrator_queue_add_row_concurrency.py::TestAddRowIsAOneFileCreate::test_concurrent_appends_both_survive`. The build log (python-2026-09-24-070209.log line 18) shows the test ran and passed under the xdist_group nodeid form `...test_concurrent_appends_both_survive@orchestrator_add_row_contention`. The executing agent had to rule it a matcher false negative by hand.

## Root cause

`assert_test_identifiers` compares nodeids exactly. It does not strip the `@{group}` suffix that pytest-xdist appends to tests marked with `xdist_group`.

## Proposed action

Normalise the nodeids it collects by stripping a trailing `@{group}` suffix before comparison. Add a test where an `xdist_group`-marked test is matched.

## Evidence

- aspect: logging_gap_analysis — work.log 07:03:36 `[VERIFY] (plan-marshall:execute-task) TASK-17 diff assertion reported 1 missing identifier ... matcher false negative, test ran and passed`
