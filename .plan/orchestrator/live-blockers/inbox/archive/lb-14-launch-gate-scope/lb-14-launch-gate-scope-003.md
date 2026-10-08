envelope_version=1
sender_type=plan
sender_id=lb-14-launch-gate-scope
epic=live-blockers
kind=candidate-lesson
created=2026-10-08T14:55:38Z

component=plan-marshall:plan-retrospective
category=bug

# outline-vs-shipped counts a superseded CERTAIN_EXCLUDE as a violated exclusion

## Context

For plan lb-14-launch-gate-scope the outline-vs-shipped aspect reported `exclude_violated: 2 of 6`. One of the two paths, `persona-plan-orchestrator/SKILL.md`, carries two records in the assessments store: a CERTAIN_EXCLUDE written at 07:57 and a later CERTAIN_INCLUDE (c04170, 08:14) that states it "supersedes the earlier exclusion" under the operator's review decision. The aspect counted the stale exclusion, so the report names a deliberately shipped file as "the one unambiguously bad outcome".

## Root cause

The aspect builds its certain-exclude population from every assessment record per path and does not resolve a path to its latest record. The assessments store is append-only and a revision adds a new record rather than editing the old one.

## Proposed action

Resolve each assessed path to its most recent record before partitioning into include and exclude populations, and publish the count of paths that had more than one record so a superseded assessment is visible rather than silently dropped. The other reported path in this plan, `plan-orchestrator/templates/plan-spec.md`, is a genuine violation and must still be reported.

## Evidence

- aspect: outline_vs_shipped - exclude_violated 2 of 6, members listed
- assessments store - two records for the same path, the later one an explicit supersession
- aspect: manifest_decisions - plan-spec.md is the only genuine realized-but-undeclared path
