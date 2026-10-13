envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T11:06:04Z

# Candidate lesson: worktree-rebase-to's executor drift probe errors without a marketplace root

Source: dispatcher-reported script-level friction

## What happened

In pm-mcp-core (a consumer project, no `marketplace/` tree), `worktree-rebase-to` ran its executor drift probe,
and the probe errored because there is no marketplace root to compare the executor against.

## Candidate rule

The executor drift probe should detect a checkout without a marketplace root and report an explicit
not-applicable state instead of an error, so consumer projects do not see a spurious failure on every rebase.

Likely owner: plan-marshall:workflow-integration-git (worktree-rebase-to) / executor drift probe.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `scenario-replay-harness-008.md` from plan scenario-replay-harness (PLAN-22, #50; Claude Code)
