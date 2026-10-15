envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:33:33Z

# Lessons ingest: gate-bundle derivation yields zero bundles on Maven projects and the pre-push gate degrades

Severity: high (silent-zero gate passes over nothing; explicit DEGRADED trains ignore). Bundle: `plan-marshall` (gate-bundle derivation, pre-push quality gate, module-tests canonical).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-203`..`-286`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-205` | `derive_gate_bundles` returns zero bundles on a non-marketplace Maven project; empty gate population reports green. |
| `pm-mcp-core-m2-m4-216` | Same silent-zero gate on a Maven-module project (duplicate of 205). |
| `pm-mcp-core-m2-m4-229` | Bundle-only derivation makes the per-module gate silently empty in a Maven repository. |
| `pm-mcp-core-m2-m4-237` | Pre-push quality gate permanently DEGRADED in a Maven project (same root as 229). |
| `pm-mcp-core-m2-m4-250` | Module-tests canonical misses Maven; divergence ungated across 8 degraded firings. |
| `pm-mcp-core-m2-m4-267` | Pre-push gate degrades on a Maven multi-module project (operator graded high at this ingest, 2026-10-15: degraded safety gate). |

Asked for: gate derivation covers Maven-module projects (or refuses to report green over an empty population); check against the Maven gate backlog for residual.

Owner today: none. Not re-checked at HEAD by the ingest.
