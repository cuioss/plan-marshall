envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T20:22:08Z

# Candidate lesson: align workflow docs with script flags (qgate query, get-deliverable --number, finalize-step --verification-owed)

Component: plan-marshall (phase-3-outline, q-gate-validation, phase-5-execute / execute-task; version 0.1.1947)
Category: anti-pattern
Source: plan-retrospective of work-package-redistribution (script-failure-analysis, work log, session transcript)

## Context

Besides the six failures lessons-capture already routed (git-workflow commit, deliverable-hashes, tasks_already_exist,
pull_failed, pr edit body, shared module_mapping.toon), this run hit four more argparse rejections in plan-marshall
components:

1. `manage-findings qgate query` (invented verb, exit 2) - twice, on each phase-3-outline re-entry
   (16:45:32Z, 16:52:33Z). Registered verbs: add, clear, list, resolve, resolve-by-rule, resolve-evidenced.
2. `manage-findings qgate add` missing required arguments (exit 2) - once, q-gate-validation in 4-plan (17:02:19Z).
3. `manage-solution-outline get-deliverable --number` (invented flag; the flag is `--deliverable-number`) - once,
   phase-5-execute envelope 2 (17:44:40Z).
4. `manage-tasks finalize-step --verification-owed` (flag absent in this version) - once, TASK-11 (17:59:46Z).
   Consequence: TASK-9, TASK-10 and TASK-11 were closed as plain `done` while their orchestrator-tier quality gate
   was still owed; the gate passed later, but the task record never said it was pending.

## Root cause

The workflow text the leaves follow names verbs and flags the installed scripts do not declare (items 1, 3, 4), or
omits required flags (item 2). Item 4 is a documented contract with no script support.

## Proposed action

- Re-run the canonical-invocation check of plan-marshall against phase-3-outline (re-entry path), q-gate-validation
  and execute-task, and fix the docs to the real argparse surface.
- Either add `--verification-owed` to `manage-tasks finalize-step` or remove it from execute-task, and say how an
  owed orchestrator-tier gate is recorded on the task.

## Evidence

- script-failure-analysis: 8 failures, 3 unique (manage-findings qgate x3, deliverable-hashes x4, finalize-step x1)
- work.log lines 39, 51, 65, 184, 244 (failure details quoted above)
