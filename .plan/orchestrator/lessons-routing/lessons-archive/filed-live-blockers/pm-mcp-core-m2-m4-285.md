envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:52Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-031.md
> RECURRENCE of -203, -213, -240, -265. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Carry a sibling-repository deliverable into finalize fix tasks

- Source: plan-retrospective (plan-09-audit-trail), aspects chat-history-analysis, llm-to-script-opportunities, request-result-alignment.
- Suggested component: `plan-marshall:phase-6-finalize` (fix-task creation on loop-back) / `plan-marshall:phase-4-plan` (cross-repo deliverables).

## Context

Deliverable 6 updated `doc/LogMessages.adoc` and specification files in the sibling repository plan-marshall-documentation, in a separate worktree and branch. After execute, five envelopes (TASK-9, 13, 14, 16, 18) changed log templates or reason codes in pm-mcp-core and each handed back a hand-written list of `LogMessages.adoc` rows "to change before landing", because the fix tasks created by finalize loop-backs covered only this repository. Nothing in the plan owned applying those lists, and the realized footprint cannot see the sibling repo, so D6 grades as 0% coverage.

## Root cause

Fix tasks generated from code-review and functional-review findings are scoped to the plan's own worktree; a deliverable living in a sibling repository is not re-opened when a later fix changes what it documents.

## Proposed action

When a fix task changes an artifact a sibling-repository deliverable documents (here: a `LogRecord` template or reason code), add a paired task (or step) against that deliverable's worktree, or make finalize fail closed until the sibling branch is updated. A holder-vs-`LogMessages.adoc` diff check would make the drift detectable.

## Evidence

- chat-history-analysis: hand-backs of TASK-13 ("needs these rows changed before landing"), TASK-14, TASK-16, TASK-18 ("still shows the old PM_RUNTIME-108 template")
- llm-to-script-opportunities: "LogMessages.adoc row derivation repeated by hand in 5 envelopes"
- request-result-alignment: D6 partial, 0 of 7 mutate paths in this repo's footprint
