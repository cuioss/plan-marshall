envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:07Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# ci_complete_precondition call failed for a missing --worktree-path

Source: script-failure cluster (notation plan-marshall:phase-6-finalize ci_complete_precondition, rejected for missing `--worktree-path`), plan plan-70-plan-instance-alignment.

The finalize CI-complete precondition was invoked without the `--worktree-path` argument its parser requires, and failed before running. Under the cwd-pinned model most callers no longer forward a worktree path, so this verb's requirement is easy to miss.

## Rule / fix direction

Either make the precondition derive the worktree from the pinned cwd (consistent with cwd-policy.md "worktree-path passing is unnecessary under cwd-pinning"), or name `--worktree-path` explicitly at every call site in the finalize workflow docs so the caller copies it verbatim.
