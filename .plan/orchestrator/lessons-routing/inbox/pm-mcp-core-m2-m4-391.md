envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-21T18:23:29Z

component=plan-marshall:phase-6-finalize
category=improvement
bundle=plan-marshall

# Sync the declared footprint when a scope deviation is accepted

## Context

The plan's request was explicitly documentation-only ("No production code, no test, no POM change"). During automatic review a CodeRabbit finding (11b0e3) asked for a real resource bound on the enrolled argument pattern. Triage escalated it, and at 2026-10-21T11:00:33Z the operator accepted a scope deviation that split it into TASK-005. That task changed six files: `ProjectEnrolment.java`, `EnrolmentPolicy.java`, `ArgumentSchemaValidator.java`, two test classes, and the Job Runtime specification. The landing commit `c45a968` carries 14 files, of which 10 lie outside every deliverable's declared surface.

The deviation itself was legitimate and operator-approved. What did not follow it was the declaration: `references.json` kept `affected_files` at the original four paths, and `solution_outline.md` kept the four deliverables unchanged. Every downstream consumer then read the pre-deviation surface and reported the gap as an unexplained anomaly rather than as the accepted expansion it was:

- `check-artifact-consistency` — `references_only` 10, `affected_files_exact_match` deferred.
- `check-manifest-consistency` — `declared_vs_realized_set` fail, 10 realized-but-undeclared paths.
- `manage-metrics generate` — `files_modified: 4` as the ratio denominator while the realized footprint is 14, so any per-file ratio overstates cost 3.5x.

The appended fix task also carried `origin: plan` (`[MANAGE-TASKS] Added TASK-005 (plan)`), so the ledger presented an unplanned, review-driven task as a planned deliverable bound to deliverable 4.

## Root cause

The scope-deviation accept path records the decision in `decision.log` and appends the task, but it has no step that re-derives the declared footprint. The plan therefore holds two disagreeing descriptions of its own scope for the rest of the run, and the retrospective can only report the disagreement, not the sanctioned reason behind it.

## Proposed action

In the `scope-deviation:accept` handler, after appending the fix task, run the existing references sync over the union of the task's declared targets — `manage-references sync-affected-files` (or `set-list`) for `affected_files`, and an outline `update` that adds the fix task's files to the owning deliverable's `Affected files` block. Stamp the decision-log entry with the number of paths added. When the appended task comes from a review finding, pass `--origin pr` (or `fix`) so the task's provenance matches its source.

## Evidence

- aspect: request_result_alignment — 10 scope_creep paths; both findings cite the accept at 11:00:33Z and the unamended declarations.
- aspect: manifest-decisions — `declared_vs_realized_set` fail, `references_only_count: 10`.
- aspect: plan-efficiency — denominator drift finding: `files_modified=4 vs realized=14`.
- logs/decision.log 2026-10-21T11:00:33Z `(scope-deviation:accept)`; logs/work.log `[MANAGE-TASKS] Added TASK-005 (plan)`.
