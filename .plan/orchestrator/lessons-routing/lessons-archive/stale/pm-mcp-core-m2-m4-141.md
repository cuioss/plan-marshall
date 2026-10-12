envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T13:52:03Z

# scope_creep_check diffs from the stale plan-creation SHA and files a finding type manage-findings rejects

Component (suggested): plan-marshall:phase-5-execute (scope_creep_check), category bug (marketplace-owned)
Signal: plan-retrospective, script-failure-analysis cluster (3 occurrences, script_internal_error, first 2026-10-11T15:35:49Z) plus two execute leaf reports

## Observation

`scope_creep_check check` exited 1 three times in 5-execute. Two independent defects stacked: (1) it diffed from `plan_creation_sha` cbdd04e instead of the branch base d091527, so it flagged 74 "outside scope" files that were commits #27/#28 landed on main before the worktree was cut; (2) it then tried to persist a finding of type `scope_creep_warning`, which `manage-findings` does not accept (`finding_persist_failed`). The leaves logged an ERROR and continued, so the check produced no usable signal for the whole plan — while this plan did in fact ship 22 undeclared files.

## Candidate directive

Diff scope creep from the worktree's branch base (or the realized-footprint resolver), not from `plan_creation_sha`, and file through a finding type `manage-findings` declares. A test with a main that advanced between plan creation and worktree creation would catch the first defect.

Source: plan plan-11-enrolment-store (PLAN-11, PR #30); plan-retrospective script-failure-analysis.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-11-enrolment-store-014.md` from plan plan-11-enrolment-store (PLAN-11, #30; Claude Code)
