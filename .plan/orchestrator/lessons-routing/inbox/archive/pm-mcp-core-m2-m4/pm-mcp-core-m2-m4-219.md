envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:05Z

# Candidate lesson: unified triage reported 15 pending stale build findings absent from the store

Source: dispatcher-reported script-level friction

## What happened

During finalize, the unified triage reported 15 pending build findings that were stale and did not exist in the
plan's findings store (a `manage-findings` list for the plan shows no such pending records). The count therefore
did not match the store it claims to summarise.

## Candidate rule

The triage count must be derived from the same store the findings list reads (or name the population it was
computed over), so a stale or foreign source cannot inflate the pending count. Worth checking whether it read a
different checkout's store (worktree vs main) or a cached build-result file.

Likely owner: plan-marshall:phase-6-finalize triage / plan-marshall:manage-findings.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-010.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
