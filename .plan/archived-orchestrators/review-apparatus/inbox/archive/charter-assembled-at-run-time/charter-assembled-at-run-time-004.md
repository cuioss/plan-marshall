envelope_version=1
sender_type=plan
sender_id=charter-assembled-at-run-time
epic=review-apparatus
kind=candidate-lesson
created=2026-09-24T11:12:13Z

component=plan-marshall:phase-3-outline
category=improvement
confidence=high

# Verify that a mandated tooling constraint is satisfiable before execute

## Context

The outline for `charter-assembled-at-run-time` required every GitHub read in the D0 population gate to go through `plan-marshall:tools-integration-ci:ci`. Raw `gh` and sampled fallbacks were prohibited. The CI abstraction had no org repository listing, no cross-repo file read, no label listing and no org code search. In execute, TASK-16 therefore went `infeasible` (15:38Z). The plan stalled until an operator ruling ("Add CI read verbs (recommended)") produced fix task TASK-17. TASK-17 added four verbs and 12 files that no deliverable declared.

## Root cause

The outline turned a tooling policy into a hard constraint without checking the named tool's verb surface. The capability gap therefore surfaced only at execute, as an unplanned mid-plan deliverable.

## Proposed action

When a deliverable mandates a specific tool/verb surface ("all X through Y"), phase-3-outline should resolve the required operations against that surface's canonical-invocation block (or `--help`). When an operation has no verb, it should either add an enabling deliverable with declared affected files, or escalate at outline time. Q-Gate should flag a mandated surface whose required verbs do not exist.

## Evidence

- aspect: chat_history_analysis: post-outline operator pivot to add CI read verbs
- aspect: request_result_alignment: 12 files of scope creep from TASK-17
- aspect: script_failure_analysis / work.log: TASK-16 infeasible, "tools-integration-ci has no org repository listing / file-content / label-list / code-search verb"
