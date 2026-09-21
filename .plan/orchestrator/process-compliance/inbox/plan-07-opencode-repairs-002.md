envelope_version=1
sender_type=plan
sender_id=plan-07-opencode-repairs
epic=process-compliance
kind=finding
created=2026-09-20T21:30:29Z

# Finalize blocked: no session identity on transcript-capable target

sender: plan-07-opencode-repairs
epic: process-compliance

Late session capture failed with `hook_not_configured`
($CLAUDE_CODE_SESSION_ID unset). The project resolves to a
transcript-capable target, so the finalize entry resolver keeps the hard
block per the execution workflow: no filler identity invented, no
`session_id` dispatched.

Remedy: install the SessionStart hook via marshall-steward (or run finalize
from a session where the hook already captured an identity), then re-enter
finalize. Work is committed per-deliverable (4 commits) on
`feature/plan-07-opencode-repairs` in the plan worktree; the plan sits in
`6-finalize` pending. No push, no PR, no merge attempted.

This is the documented resolver abort the spec cites as surrounding evidence
(one layer above the graceful record-metrics no-op); the resolver itself
belongs to finalize-machinery PLAN-07 and was not touched.
