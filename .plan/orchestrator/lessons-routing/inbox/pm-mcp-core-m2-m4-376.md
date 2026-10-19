envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T18:47:05Z

component=plan-marshall:phase-6-finalize
category=improvement

# Residual recorded for repository-external work that the plan's head can never close

Source: Q-Gate 6-finalize finding ea6e2e (functional-review, residual at D10.R1; resolved in run as accepted), plan plan-70-plan-instance-alignment.

The residual was "the separate one-line roadmap-link PR in plan-marshall-documentation (roadmap.adoc line 233) is not open at this head; the repository-side work of the deliverable is complete". The repository-side work was done; only the foreign-repo PR was outstanding, which no commit on this branch can change, so the residual could only be cleared by operator acceptance.

## Rule

Model foreign-repository follow-ups (documentation PRs, roadmap links) as owed items with their own tracking (PR number recorded on the plan), not as residuals of a deliverable whose review is pinned to this repository's head. Same D10 issue as 22e83d / 82db0b.
