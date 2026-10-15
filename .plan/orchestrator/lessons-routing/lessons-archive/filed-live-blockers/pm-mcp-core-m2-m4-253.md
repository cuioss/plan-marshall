envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T20:35:26Z

# Candidate lesson: Sonar fetch_findings reports count_status confirmed on a stale PR analysis

**Component (suggested):** plan-marshall:workflow-integration-sonar
**Category (suggested):** bug

## Observation

After the PR head was force-pushed / CI re-run, SonarCloud recorded the new uploads as BRANCH analyses, so
the PR analysis stayed stale: 38 issues reported against code that no longer existed. `sonar fetch_findings`
nevertheless returned `count_status: confirmed` for that stale analysis. The step only failed closed because
the agent manually compared the issue lines with the current code.

## Root cause

fetch_findings does not verify that the PR analysis it reads belongs to the current PR head commit; a
branch-typed analysis of the same head is not recognised as the authoritative one, and staleness is not part
of the count_status derivation.

## Suggested correction

Compare the analysis revision (commit SHA) of the PR analysis against the PR head SHA; when they differ,
report a distinct stale/unconfirmed count_status (never `confirmed`) and name the head-vs-analysis SHAs, so
the gate fails closed deterministically instead of relying on the agent's manual line check.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-17-project-units-and-invariants-002.md` from plan plan-17-project-units-and-invariants (PLAN-17, #56; harness Claude Code)
