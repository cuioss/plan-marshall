envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T14:52:43Z

Candidate lesson (source: review-bot findings c9636e (sourcery-ai), 2b2657 and 599b7e (coderabbitai) on PR #28, remediated in run; plan http-baseline).

Two address-family defects in the new HTTP tests:

1. `closedOrigin()` in CiHttpClientTest probed a free port with `InetAddress.getLoopbackAddress()` (may be `::1`) but built the URI on `127.0.0.1`, so the probed port and the target could be in different address families. Fix: bind the probe socket to `127.0.0.1`. (The probe-and-release race remains, as for any such refused endpoint.)
2. The client URLs of all four provider tests were hard-coded to `127.0.0.1`, while `@EnableMockWebServer` binds whatever `localhost` resolves to; on an IPv6-first host the connections fail before any provider behaviour runs. Fix (commit 71c8256): build the URL from the server's host name / actually bound address; the cross-origin case keeps two distinct host names.

Rule candidate: never hard-code a loopback literal in a test that talks to a mock server; derive the URL from the server's bound address, and keep every probe socket in the same address family as the URI it feeds. Both defects passed local and CI builds and were only caught by review bots.

Component candidates: pm-dev-java-cui:cui-http-testing, pm-mcp-core provider test fixtures.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `http-baseline-004.md` from plan http-baseline (PLAN-05, #28)
