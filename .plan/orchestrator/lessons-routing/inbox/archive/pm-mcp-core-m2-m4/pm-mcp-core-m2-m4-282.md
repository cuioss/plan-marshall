envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T06:32:50Z

> Routed by orchestrator epic pm-mcp-core-m2-m4 from plan plan-09-audit-trail (PLAN-09, pm-mcp-core #69, merged 3236ed5), drained 2026-10-15.
> Source inbox message(s): plan-09-audit-trail-028.md
> NEW; related to -086. Uncorroborated in the plan's logs; the message says so itself. Earlier numbers are lessons-routing messages pm-mcp-core-m2-m4-NNN.

# Freshness gate refused because the build ran before the commit

- Source: orchestrator-observed during finalize. NOT corroborated in the plan work or decision log (the work log records only successful "Worktree freshness: basis=ledger-verified" transitions). Treat as orchestrator testimony.
- Suggested component: `plan-marshall:phase-5-execute` / `plan-marshall:phase-6-finalize` (freshness gate ordering).

## Observation

The freshness gate refused once because the verifying build had run against the tree before the last commit was made, so the ledger's worktree hash no longer matched HEAD; the build had to be repeated after committing.

## Candidate rule

Commit first, then run the verifying build that the freshness gate will check; a workflow step that builds and then commits should be reordered, or the gate's refusal message should name this ordering as the likely cause.
