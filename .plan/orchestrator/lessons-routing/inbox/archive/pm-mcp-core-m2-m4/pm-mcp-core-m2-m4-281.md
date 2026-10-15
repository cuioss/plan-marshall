envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:49Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-027.md
> NEW. Uncorroborated in the plan's logs beyond build durations of about 7 minutes; the message says so itself. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Build wrapper default timeout (300 s) too short for this repo's full verify

- Source: orchestrator-observed (finalize freshness-gate retry timed out at the default and needed `--timeout 590`). NOT corroborated in the plan work or decision log — the work log records only that full `verify` runs in this plan took up to about 7 minutes (e.g. 16:39:27Z -> 16:46:57Z, 14:50:26Z -> 14:56:43Z). Treat as orchestrator testimony plus supporting durations.
- Suggested component: `plan-marshall:build-maven` (wrapper default timeout) / project-local (pm-mcp-core CLAUDE.md build section); a matching user memory note exists ("pass --timeout 590").

## Observation

A full `verify` of pm-mcp-core routinely exceeds 300 s, so a gate that calls the wrapper with its default times out and has to be retried with `--timeout 590`. The project CLAUDE.md says "Run a build with a Bash timeout of 600000ms" but that sets only the Bash ceiling, not the wrapper's own timeout.

## Candidate rule

Either the wrapper should derive its timeout from the architecture-resolved `bash_timeout_seconds` (or from recorded durations), or the project build commands should state the wrapper `--timeout` explicitly, so gate callers do not use a default that is known to be too short.
