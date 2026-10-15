envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:35:01Z

# Lessons ingest: per-package ADR numbers collide and the pre-merge gate misses them

Severity: high (duplicate numbers slip past gate and conflict detection; operator graded 252 high at this ingest, 2026-10-15). Bundle: `plan-marshall` (`manage-adr` scanner, pre-merge gate).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-242`, `-252`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-242` | Per-package ADR numbers collide; the ADR scan is root-only and misses per-module duplicates (double renumber). |
| `pm-mcp-core-m2-m4-252` | Module-level `doc/adr/{package}/` ADR number collisions; repeat collision needing landing renumber. |

Asked for: the ADR scan covers per-module directories and the pre-merge gate catches duplicate numbers.

Owner today: none. Not re-checked at HEAD by the ingest.
