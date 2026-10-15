envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:35:16Z

# Lessons ingest: task skill resolution attaches framework skills the module forbids

Severity: high (operator graded high at this ingest, 2026-10-15: systematic wrong-skill attachment). Bundle: `plan-marshall` (`phase-4-plan` skill resolution).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-224`, `-232`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-224` | Persona-merged task skills ignore the module's real frameworks (systematic wrong skills; flagged and skipped in-run). |
| `pm-mcp-core-m2-m4-232` | Quarkus/CDI skills attached to tasks of a repo that forbids them; the operator stripped them (same root as 224). |

Asked for: skill resolution filters by the module's real frameworks and repo-level exclusions before attaching.

Owner today: none. Not re-checked at HEAD by the ingest.
