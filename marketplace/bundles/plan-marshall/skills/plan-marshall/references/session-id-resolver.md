# Session ID Resolver

Main-context skill calls that need the current Claude Code `session_id` (e.g., `phase-6-finalize` forwarding it to `manage-metrics enrich`) read it from a hook-populated cache via [`../scripts/manage_session.py`](../scripts/manage_session.py). The terminal-title hook is the canonical source — on every `UserPromptSubmit` it writes the `session_id` carried in the hook stdin payload into:

| Path | Key | Purpose |
|------|-----|---------|
| `~/.cache/plan-marshall/sessions/by-cwd/{sha256(cwd)}` | Project root (as returned by `git rev-parse --show-toplevel`) | Handles concurrent sessions in different checkouts — the cwd-specific lookup wins when multiple Claude Code windows are open |
| `~/.cache/plan-marshall/sessions/current` | Singleton (last-write-wins) | Safety net when the cwd-keyed entry is missing |

Callers invoke the resolver via the standard executor:

```bash
python3 .plan/execute-script.py plan-marshall:plan-marshall:manage_session current
```

The script returns TOON. On success: `status: success\nsession_id: <id>`. When neither cache file is present: `status: error\nerror: session_id_unavailable` — callers apply their own policy (abort vs. degrade). The resolver itself never reads `$VAR`, never shells out beyond `git rev-parse`, and never falls back to environment variables: the only in-process source of `session_id` is the hook stdin payload, so the cache is the only correct read path.
