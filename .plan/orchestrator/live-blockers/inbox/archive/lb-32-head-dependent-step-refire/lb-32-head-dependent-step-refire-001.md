envelope_version=1
sender_type=plan
sender_id=lb-32-head-dependent-step-refire
epic=live-blockers
kind=candidate-lesson
created=2026-10-10T03:27:47Z

component=plan-marshall:phase-5-execute
category=bug
source_plan=lb-32-head-dependent-step-refire
confidence=high

# Make scope_creep_check persist its finding and diff against the merge base

## Context

During plan `lb-32-head-dependent-step-refire`, `plan-marshall:phase-5-execute:scope_creep_check check` exited 1 on every pass it was run: 5 logged failures across the execute dispatches. Four separate execute returns reported the same cause, `finding_persist_failed`: `manage-findings` rejects the finding type `scope_creep_warning` as invalid. Each agent ran the check once, logged it and moved on, so the guard stored no finding for the whole plan.

What the check measured was also wrong for its purpose. It reported 150 residual files (161 on the last pass) against a threshold of 5, and every path shown was under `.plan/orchestrator/` — ledger commits that landed on the base branch after `plan_creation_sha`, none of them this plan's work.

## Root cause

Two independent defects. The check writes a finding type the findings store does not accept, so a positive result can never be persisted. And it compares against the plan's creation commit rather than the merge base with the current base branch, so upstream commits count as the plan's own scope creep.

The script log carries an empty stderr excerpt for all 5 failures; the cause is known only from agent narrative. The second defect was read from truncated check output quoted by the agents, not from the script source.

## Proposed action

- Register `scope_creep_warning` as an accepted finding type, or make the check write a type the store already accepts.
- Compute the residual set against the merge base with the base branch, so upstream landings are excluded.
- Make the check write its failure cause to stderr so the script log records it.
- Add a test that runs the check end to end against a real findings store.

## Evidence

- aspect: script_failure_analysis — `plan-marshall:phase-5-execute:scope_creep_check`, subcommand `check`, exit 1, `script_internal_error`, 5 occurrences, empty stderr excerpt
- aspect: chat_history_analysis — four execute returns: "`scope_creep_check check` exited 1 with `finding_persist_failed`: `manage-findings` rejects the type `scope_creep_warning` as invalid"
- aspect: logging_gap_analysis — no cause captured in the script log for any of the 5 failures
