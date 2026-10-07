envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=finding
created=2026-09-18T17:05:29Z

## Finalize blocked at session-identity gate — hook not wired (plan-07-session-identity)

- Gate outcome: ABORT at finalize entry. `status.metadata.session_ids` absent; single late `session capture` failed with `hook_not_configured` (`$CLAUDE_CODE_SESSION_ID` unset).
- Target reading: `platform_runtime runtime-info` reports `harness: claude` — a transcript-capable target. Per the plan's own decision table (absent identity + transcript-capable = broken hook, never a pass), abort is the designed outcome, not a defect. The old and new contracts agree here.
- Implementation state (preserved, unshipped): 3 tasks done, 3 commits on `feature/plan-07-session-identity` in the plan worktree (`.plan/local/worktrees/plan-07-session-identity`), per_task verification passed (compile, quality-gate, focused enrich tests), whole-tree `module-tests` green via build-server job (exit 0). Nothing pushed — push lives in finalize.
- Stash note: main-checkout `stash@{0}` (`plan07-session-identity-wip-on-main`, pre-existing unowned work) was never popped or copied; tasks implemented from the plan's own bodies. The stash still exists for operator disposition.
- Remedy (operator-side): run marshall-steward to install the SessionStart hook so a session identity is captured, then re-run finalize for `plan-07-session-identity`. No code change needed; replaying finalize unchanged after the hook is installed should proceed enriched.
- Metrics note: `6-finalize` boundary is stamped but the phase never closed; the final report will carry the missing-`end_time` gap flag for it.
