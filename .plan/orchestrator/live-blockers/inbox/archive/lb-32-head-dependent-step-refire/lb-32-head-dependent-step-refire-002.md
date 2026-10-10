envelope_version=1
sender_type=plan
sender_id=lb-32-head-dependent-step-refire
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T03:27:50Z

component=plan-marshall:manage-tasks
category=improvement
source_plan=lb-32-head-dependent-step-refire
confidence=high

# Let manage-tasks update edit verification commands and criteria

## Context

On plan `lb-32-head-dependent-step-refire` the 4-plan quality check raised 5 test-placement findings after 13 tasks already existed. The operator chose to move the tests to the module that owns the code under test. That changed the verification commands of five tasks from `module-tests plan-marshall` to `module-tests pm-plugin-development`, and one task needed a second command.

The plan phase patched step targets and descriptions in place, then returned `blocked` with `verification_not_patchable`: `manage-tasks update` takes title, description, depends-on, status, domain, profile, skills, deliverable and the cost flags, and `add-step` / `update-step` / `remove-step` / `rename-path` touch only steps. Nothing edits `verification.commands` or `verification.criteria`. Direct edits of the task files are forbidden, and remove plus re-add breaks the gap-free numbering. The orchestrator cleared all 13 tasks and re-planned from scratch.

## Root cause

The task tool has no write path for a task's verification block after creation, so any change to where a test lives or how it is verified can only be made by deleting and re-creating tasks.

## Proposed action

Add verification write-back to `manage-tasks update` (commands and criteria), with the same validation the batch-add path applies. Document it in the phase-4-plan re-entry path so a quality-check fix that only moves verification can be patched in place.

## Evidence

- aspect: chat_history_analysis — phase-4-plan return: "manage-tasks has no way to change a task's verification.commands or verification.criteria"; followed by a full re-plan (13 tasks re-created in one batch)
- aspect: llm_to_script_opportunities — "edit a task's verification commands", low complexity
- cost context: 4-plan consumed 1164027 tokens over 3155 s wall, with two task_batch_complete dispatches (182973 and 193567 tokens)
