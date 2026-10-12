envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T07:42:16Z

# Provision a per-plan worktree for sibling-repo deliverables before execute

## Context

PLAN-06's outline addressed four documentation deliverables by the absolute path of the sibling
repository's main checkout (`/Users/oliver/git/plan-marshall-documentation/...`). The first execute
envelope blocked at TASK-1 (`docs_repo_on_foreign_feature_branch`): that checkout was on
`docs/use-case-onboarding` for other work. The operator chose a separate docs worktree, and the
following envelopes had to redirect TASK-1, 19, 20, 21 and later TASK-31 to it by note. PLAN-04 had
already used its own separate checkout, so the condition is recurring across the epic.

## Root cause

No phase before execute checks the state of a sibling repository or creates a branch/worktree for
the plan there; tasks are bound to the shared main checkout, whose branch belongs to whoever used it
last. This is distinct from candidate plan-06-store-substrate-001 (relative `../` paths): absolute
paths resolved fine, but pointed at a checkout the plan does not own.

## Proposed action

When a deliverable's module is a sibling repository, have phase-4-plan (or the phase-5 entry) create a
plan-owned worktree of that repository on `feature/{plan_id}` from an up-to-date main, record its path
in the plan metadata, and write that path into the task targets - never the shared main checkout.

## Evidence

- aspect: chat_history_analysis - execute envelope 1 returned blocked, reason docs_repo_on_foreign_feature_branch; operator: "Separate worktree"
- docs worktree now at /Users/oliver/git/pm-mcp-core/.plan/temp/plan-06-plan-marshall-documentation

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-06-store-substrate-013.md` from plan plan-06-store-substrate (PLAN-06, #26)
