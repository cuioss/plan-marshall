envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:07Z

component=plan-marshall:manage-status
category=bug

# execute -> finalize transition refused with execute_commits_unrecorded after a baseline rebase rewrote the commit SHAs

Source: script-failure cluster (notation plan-marshall:manage-status:manage-status, `transition --plan-id plan-70-plan-instance-alignment --completed 5-execute`, exit 1, `error: execute_commits_unrecorded` with 14 unrecorded commits), plan plan-70-plan-instance-alignment.

The plan's branch was rebased onto a new baseline during execute. The rebase rewrote every execute commit's SHA, so the recorded per-task commit SHAs no longer matched the branch, and the phase transition counted all 14 rewritten commits as unrecorded and refused.

## Rule / fix direction

The execute-commits check should either re-associate commits after a rebase (by patch-id or by the task trailer in the commit message) or the rebase step should re-stamp the recorded SHAs. Until then, an operator running a baseline rebase in 5-execute must expect this refusal and re-record the commits before transitioning.
