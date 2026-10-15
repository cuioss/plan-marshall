envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:45:27Z

# Lessons ingest: worktree-remove from a shell pinned to the worktree fails after move-back

Severity: high (stale-cwd failure; same class as the known `--plan-id` resolution failure). Bundle: `plan-marshall` (`workflow-integration-git`, plan resolution).

Source: API-Sheriff plan `32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466), message `-012`. Full body: `lessons-routing/lessons-archive/filed-live-blockers/api-sheriff-kidicap-gateway-requirements-012.md`.

| Message | Statement |
|---|---|
| `api-sheriff-kidicap-gateway-requirements-012` | `worktree-remove` from a shell pinned to the worktree fails after the move-back (`plan_resolution_failed` on a stale cwd); main-anchored resolution missing. |

Asked for: worktree lifecycle commands resolve main-anchored instead of trusting the calling shell's cwd.

Owner today: none. Not re-checked at HEAD by the ingest.
