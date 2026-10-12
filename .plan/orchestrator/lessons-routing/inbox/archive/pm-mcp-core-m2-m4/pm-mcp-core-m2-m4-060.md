envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T14:52:43Z

Candidate lesson (source: script failure cluster plan-marshall:phase-5-execute:scope_creep_check, plan http-baseline).

`scope_creep_check` failed twice (2026-10-11T08:28Z during TASK-9, 09:14Z during TASK-10) with exit_code=1, failure_kind=script_internal_failure, error finding_persist_failed: it tries to persist a finding of type `scope_creep_warning`, which manage-findings rejects (allowed types: bug, improvement, anti-pattern, triage, tip, insight, best-practice, build-error, test-failure, lint-issue, sonar-issue, arch-constraint, pr-comment, pr-comment-overflow).

Second defect in the same check: its 80-file residual wrongly included upstream main commits brought in by the finalize rebase (pm-core store substrate, pm-runtime service unit), measured since plan_creation_sha. Each task actually touched only its 4 declared test files. The diff base should be the merge-base with the current base branch (or the task's start commit), not the plan creation SHA.

Corrective: align scope_creep_check's finding type with the manage-findings type enum (or add the type), and compute the residual against a rebase-stable base.

Component candidates: plan-marshall:phase-5-execute (scope_creep_check), plan-marshall:manage-findings (type enum).

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `http-baseline-005.md` from plan http-baseline (PLAN-05, #28)
