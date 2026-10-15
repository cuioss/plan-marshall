envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:35:12Z

# Lessons ingest: phase-4/5 subagents self-transition phases before the orchestrator-owned Q-Gate runs

Severity: high (gate-bypass ordering violation). Bundle: `plan-marshall` (`phase-3/4/5` phase ownership, `manage-status`, Q-Gate sequencing).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox message `-255`. Full body: `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-255.md`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-255` | Phase-4/5 subagents self-transition phases before the orchestrator-owned Q-Gate runs. |

Asked for: only the orchestrator transitions phases across the Q-Gate boundary (or the gate re-arms after a self-transition); check against the phase-gate backlog for residual.

Owner today: none. Not re-checked at HEAD by the ingest.
