envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T15:13:49Z

# Sonar PR issue list is not tied to the analysed revision; stale issues reported as current

**Component (foreign):** plan-marshall:workflow-integration-sonar (`sonar fetch_findings`, `sonar_rest search --pr`), plan-marshall:phase-6-finalize sonar-roundtrip step
**Category:** bug
**Source plan:** plan-14-operator-and-question-stores (PR #93)

## Observation

`sonar_rest search --pr` and `sonar fetch_findings` kept returning 39 issues whose keys belonged to the analysis of an older head, while the SonarCloud PR decoration comment on the newer heads reported 0 new issues. The sonar-roundtrip step failed as "sonar analysis stale" because nothing ties the returned issue list to the revision that was analysed, so the step could neither trust nor discard the list.

Second facet: once the PR had become conflicting with main, GitHub created no `pull_request` workflow run for the new head at all (only the `push` run), so no PR analysis existed for that head. The tooling could not distinguish "analysis pending" from "analysis will never come".

## Suggested corrective action

- Read the analysed revision of the PR analysis (e.g. the analysis/ce-task revision for the pull request) and compare it to the PR head sha; report `analysis_revision` and `head_sha` in the fetch payload and refuse/mark stale only on a real mismatch.
- When the PR is in a conflicting (mergeable=false) state, report `pr_analysis_not_triggered: conflicting` and route to "rebase first" rather than waiting for or failing on a stale analysis.
- Consider the PR decoration comment's head-bound summary as a corroborating signal.
