envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:34:06Z

# Lessons ingest: Q-Gate deliverable-hash skip still has no hash primitive (recurrence of -023)

Severity: high (prior ruling: 4-plan Q-Gate hash skip = high; recurrence of `lessons-routing-023`). Bundle: `plan-marshall` (Q-Gate incremental validation, deliverable hashes).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-203`..`-286`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-225` | Missing deliverable-hash subcommand forces an ad-hoc helper and stale rows. |
| `pm-mcp-core-m2-m4-283` | No hash verb makes the unchanged-deliverable skip dead code. |

Asked for: same as `-023` (a hash primitive so the skip fires); check against `-023` for residual.

Owner today: none (nearest: `-023`). Not re-checked at HEAD by the ingest.
