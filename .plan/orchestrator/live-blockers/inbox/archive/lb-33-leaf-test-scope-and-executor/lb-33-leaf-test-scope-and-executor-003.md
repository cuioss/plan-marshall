envelope_version=1
sender_type=plan
sender_id=lb-33-leaf-test-scope-and-executor
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T19:58:04Z

component=plan-marshall:manage-lessons
category=bug
confidence=high
source_aspects=chat_history_analysis,request_result_alignment

# Resolve consult's outline from the worktree when the plan dir lives there

## Context

During lb-33's outline re-entry inside 5-execute (adding D11, then D12), `manage-lessons consult --plan-id lb-33-leaf-test-scope-and-executor` returned `outline_not_found` twice. Both times it looked in the main checkout's `.plan/local/plans/{plan_id}/` while the plan directory had moved into the worktree. The outline recorded the consult as could_not_look, so no lesson was consulted for the components of D11 and D12.

## Root cause

`consult` resolves the plan directory from the main-anchored root and does not follow the plan into a materialized worktree. Other plan-scoped verbs resolve it cwd-relative.

## Proposed action

Resolve the outline through the same plan-directory seam the other manage-* verbs use (worktree-aware), and keep `outline_not_found` only for a plan whose outline genuinely does not exist. Add a test that runs consult from a worktree-hosted plan.

## Evidence

- aspect: chat_history_analysis — outline re-entry returned `lessons_consult: could_not_look`, `lessons_consult_error: outline_not_found`, which it called "a second tooling defect on the phase-5 re-entry path"
- aspect: request_result_alignment — D11 and D12 were added after the outline with no prospective lesson consult
