envelope_version=1
sender_type=plan
sender_id=lb-25-phase-and-merge-gates
epic=live-blockers
kind=candidate-lesson
created=2026-10-11T16:01:25Z

component=plan-marshall:execute-task
category=bug
bundle=plan-marshall
source_plan=lb-25-phase-and-merge-gates

# Match xdist_group-suffixed test ids in assert_test_identifiers

## Context

TASK-10 of lb-25-phase-and-merge-gates added 19 test identifiers. `assert_test_identifiers` reported 2 of them missing from the build-results log, although both ran and passed: they are `xdist_group` contention tests, which pytest-xdist logs with an `@manage_locks_contention` suffix. The leaf re-checked with the suffix by hand and did not file a lesson.

## Root cause

`execute-task/scripts/assert_test_identifiers.py` matches node ids exactly and does not strip or tolerate the `@{group}` suffix xdist appends for `xdist_group`-marked tests.

## Proposed action

Normalise logged node ids by stripping a trailing `@{xdist_group}` suffix before matching (or match id-prefix up to `@`), and add a test fixture with a suffixed id.

## Evidence

- aspect: chat_history_analysis - "Test-identifier check gave a false missing on 2 of 19 identifiers. Those are the two xdist_group contention tests, which appear in the log only with an @manage_locks_contention suffix ... assert_test_identifiers does not handle this suffix"
