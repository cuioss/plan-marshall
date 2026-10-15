envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:34:47Z

# Lessons ingest: staged-spec premise invalidated by a sibling landing after the rebase

Severity: high (late detection cost an extra execute+verify+CI round). Bundle: `plan-marshall` (`phase-1-init` premises, sibling-landing re-check).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox message `-234`. Full body: `lessons-routing/lessons-archive/filed-live-blockers/pm-mcp-core-m2-m4-234.md`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-234` | Staged-spec/refine premises not re-checked against sibling landings; a sibling landing invalidated the premise and forced rebase plus loop-back. |

Asked for: re-check staged premises against sibling landings before execute (or record the check); check against the premise-recheck backlog for residual.

Owner today: none. Not re-checked at HEAD by the ingest.
