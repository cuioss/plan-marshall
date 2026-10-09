envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T14:43:43Z

# Lessons ingest: the scope-creep guard cannot persist its finding and measures the wrong base

Severity: high. Bundle: `plan-marshall` (`phase-5-execute`). Backlog reference: `backlog.md` § 1.7.

Two lessons were retired from the lessons corpus by the `lessons-routing` ingest of 2026-10-09 and are
handed to this epic. Their full bodies, with every recurrence and its evidence, are kept at
`lessons-routing/lessons-archive/filed-live-blockers/`.

| Lesson | Statement |
|---|---|
| `2026-10-02-10-003` | `scope_creep_check check` persists with finding type `scope_creep_warning`, which `manage-findings` rejects, so every over-threshold run exits 1 with `finding_persist_failed` and the finding reaches no store. Recurred on every task of two further plans. |
| `2026-10-02-10-004` | The guard diffs `plan_creation_sha..HEAD` and the task artifact lines diff `task_start_sha..HEAD`, so once the base branch is merged in, upstream files count as the plan's work (residual counts of 110 to 141 against a threshold of 5). |

Checked at ingest: the literal `scope_creep_warning` is still present at HEAD `909ed4d99` in
`phase-5-execute/scripts/scope_creep_check.py`, `phase-5-execute/SKILL.md`,
`test_scope_creep_check.py` and `test_qgate_persist_contract.py`, so the defect is live.

## What to check here

PLAN-LB-27 (`plan-footprint`, staged) carries both defects from PLAN-LB-07. One trigger recorded in
`2026-10-02-10-004` may not be in that spec: **task artifact lines over-attribute with no upstream
movement at all.** A plan commits once per deliverable, so the second task of a deliverable starts on a
working tree that still holds the first task's uncommitted changes, and its `[ARTIFACT]` lines list
both tasks' files (145 lines for an 89-path footprint in one plan). A merge-base range does not fix
this; the lesson proposes bounding a task's artifact diff by the working-tree state at task start.
Fold that trigger into PLAN-LB-27 if it is absent, or discard it as out of scope.
