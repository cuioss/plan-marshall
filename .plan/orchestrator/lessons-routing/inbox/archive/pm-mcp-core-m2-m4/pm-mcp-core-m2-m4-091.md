envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:34Z

# Candidate lesson: deep-lane outline finished without recording component assessments

Component: plan-marshall:phase-3-outline (deep lane)
Category (proposed): bug
Source: plan code-analysis-base, Q-Gate finding f44a6b (3-outline), resolved in-run

## Observation

The deep-lane outline was written with an empty assessment store (`assessment list` total_count 0, findings_store_state missing). None of the affected files of deliverables 1-10 was backed by a CERTAIN_INCLUDE assessment; the evidence existed only in `work/trace-matrix.md`. The Q-Gate caught it and 22 assessments were recorded afterwards.

## Proposed correction

The deep lane should record the CERTAIN_INCLUDE assessment for each existing affected file as it settles the file set (before writing the outline), or its own completion check should refuse to finish with an empty assessment store, so the Q-Gate does not have to catch it. Write-new files (not yet existing) are legitimately un-assessed and should be exempt.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `code-analysis-base-009.md` from plan code-analysis-base (PLAN-36, #31)
