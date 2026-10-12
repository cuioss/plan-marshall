envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T14:52:44Z

Candidate lesson (source: argparse-rejection script failures and process observations, plan http-baseline).

Script-surface friction hit during execute/finalize:

1. `manage-findings resolve --task-number ...` rejected (08:22:51Z, argparse_rejection): resolve declares only --plan-id, --hash-id, --resolution, --detail. A workflow step linking a finding's resolution to the task that fixes it has no flag for it, so the link is only prose in --detail ("Will be addressed by TASK-9").
2. `architecture --plan-id http-baseline search --content ...` rejected (08:24:52Z, argparse_rejection): router-scoped --plan-id placement.
3. `commit-add` rejected deliverable 0 (reported by the orchestrating session): a commit not tied to a numbered deliverable (e.g. committing the pre-commit rewrite or a review fix) has no accepted value.

Corrective candidates: give manage-findings resolve an optional --task-number (or document that the task link goes into --detail), and allow commit-add a sentinel for non-deliverable commits; for (2) the existing argparse-rejection recurrence signatures already cover it, so it may be a recurrence count only.

Component candidates: plan-marshall:manage-findings, plan-marshall:manage-architecture, the commit-add verb owner.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `http-baseline-007.md` from plan http-baseline (PLAN-05, #28)
