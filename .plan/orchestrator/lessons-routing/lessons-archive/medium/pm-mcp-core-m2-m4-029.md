envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-10T15:10:15Z

# Candidate lesson: Fire the per-deliverable commit on deliverable completion, not on the chain-tail predicate

- Component: plan-marshall:phase-5-execute
- Category: bug
- Origin: pm-mcp-core lessons store, lesson 2026-10-10-14-012 (created 2026-10-10), epic pm-mcp-core-m2-m4

- component: plan-marshall:phase-5-execute
- category: bug
- confidence: high
- source plan: lock-manager-and-leases

## Context

Every execute envelope of this plan (envelopes 1, 2 and 3, and the TASK-015 run) reported the same deviation: the workflow's per-deliverable commit test ("skip the commit while another pending task depends on the one just completed") would never fire, because the first task of each deliverable depends on the last task of the previous one. Each agent overrode it by hand and committed when all tasks of a deliverable were done.

## Root cause

The commit predicate is keyed on the task dependency chain instead of on deliverable membership, so a linear plan never satisfies it until the last task.

## Proposed action

Replace the chain-tail predicate with "all tasks of this task's deliverable are done", computed by a manage-tasks verb (for example a deliverable-complete query for a task number), and have phase-5-execute call it instead of the LLM re-deriving it per envelope.

## Evidence

- aspect: llm_to_script_opportunities — the predicate was re-decided by hand in 5 envelopes
- aspect: chat_history_analysis — envelopes 1, 2 and 3 each list "Commit predicate deviation" under decisions taken

Source: inbox `lock-manager-and-leases-016.md`, plan lock-manager-and-leases (PLAN-01, #20).
