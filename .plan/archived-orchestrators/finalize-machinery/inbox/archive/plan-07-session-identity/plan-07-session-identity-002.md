envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-18T20:08:57Z

component=plan-marshall:manage-metrics
category=bug

# Transcript-less target policy omitted Antigravity

When `.plan/marshal.json` sets `runtime.target` to `antigravity`, the registered `AntigravityRuntime.session_capture` returns a no-op and supplies no session ID. The finalize fallback therefore omits `session_id`, and `default:record-metrics` invokes `cmd_enrich` without `--session-id`.

Because `_TRANSCRIPT_LESS_TARGETS` contained only `opencode`, `cmd_enrich` returned `missing_session_id` instead of recording the unenriched gap and continuing.

## Evidence

- PR #1530 inline finding a3bbe4 (coderabbit, inline, manage-metrics.py:3812), resolution fixed via TASK-4.
- Follow-up commit on branch feature/plan-07-session-identity updated the single policy definition to `frozenset({'opencode', 'antigravity'})`.
- Plan: plan-07-session-identity. Source signal: automated-review remediated finding (pr-comment fixed).

## Proposed rule

Gate transcript-less handling on transcript availability (capture/transcript no-op answers), not on a hard-coded target allowlist; when extending the allowlist, update the single `_TRANSCRIPT_LESS_TARGETS` definition so `cmd_enrich` records the unenriched gap instead of refusing.
