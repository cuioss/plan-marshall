envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-12T13:53:24Z

# Lessons ingest: cui-http-testing gives no guidance on single-use stubbed responses or loopback address families

Severity: low. Bundle: **domain content** — `pm-dev-java-cui` (`skills/cui-http-testing/standards/testing-mockwebserver.md`). Filed under RULING 2026-10-09 (b): domain-bundle content at any severity.

Source: pm-mcp-core PLAN-05 `http-baseline` (PR #28); both defects passed local and CI builds and were caught only by review bots. Full bodies: `lessons-routing/lessons-archive/filed-live-blockers/`.

| Message | Statement |
|---|---|
| `pm-mcp-core-m2-m4-058` | Route-based dispatchers reused a configured response for every request, so a duplicate mutation call still succeeded and tests passed. Fix: each stubbed response is consumed once; an exhausted route answers 404. |
| `pm-mcp-core-m2-m4-059` | A port probe bound `getLoopbackAddress()` (may be `::1`) but the URI used `127.0.0.1`; client URLs were hard-coded to `127.0.0.1` while `@EnableMockWebServer` binds whatever `localhost` resolves to — breaks on IPv6-first hosts. Fix: derive the URL from the server's bound address; keep probe sockets in the URI's address family. |

Ground truth at `fc0090a24`: `testing-mockwebserver.md` covers `@ModuleDispatcher` routing but has no rule on response reuse and no rule on deriving the URL from the bound address (no match for single-use / loopback / IPv6). **Gap present.**

Asked for: two short rules with examples in `testing-mockwebserver.md`.

Owner today: none found.
