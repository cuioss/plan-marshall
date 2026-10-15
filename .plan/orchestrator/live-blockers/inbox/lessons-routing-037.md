envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-15T12:35:08Z

# Lessons ingest: verification scoped to the wrong files and Sonar confirms a stale analysis

Severity: high (checker false-pass; fail-open on stale SHA saved only by a manual check; operator graded 247 high at this ingest, 2026-10-15). Bundle: `plan-marshall` (outline verification scope, `workflow-integration-sonar`).

Source: pm-mcp-core epic `pm-mcp-core-m2-m4` inbox messages `-247`, `-253`. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-247` | A deliverable's verification command checked other files while nothing checks Markdown links (checker false-pass `total_links: 0` on `.md`). |
| `pm-mcp-core-m2-m4-253` | Sonar `fetch_findings` reports `confirmed` on a stale PR analysis (fail-open on stale SHA). |

Asked for: verification scope matches the deliverable's own files (plus a Markdown-link check that cannot false-pass on zero); Sonar refuses to confirm a stale analysis.

Owner today: none. Not re-checked at HEAD by the ingest.
