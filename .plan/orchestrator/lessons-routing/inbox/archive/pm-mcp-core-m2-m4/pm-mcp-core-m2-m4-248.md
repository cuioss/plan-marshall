envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-13T18:29:11Z

# The deep-lane outline was written without recording any component assessments

## What happened

Plan 39's outline took the deep lane and declared 62 paths across 9 deliverables. The deep-lane assessment step was skipped: `assessment list --certainty CERTAIN_INCLUDE` returned 0 records (findings store state `missing`). The 3-outline Q-Gate caught this (finding 8eb2e9). The fix recorded 91 CERTAIN_INCLUDE assessments afterwards (one per unique declared path, with each existing path checked as tracked in git and each new path checked as absent). This caused an extra outline iteration.

## Rule / fix

- In the deep lane, assessments are an input to the outline, not something to add later. Record a CERTAIN_INCLUDE (or CERTAIN_EXCLUDE) assessment for each declared path before writing the outline.
- Consider a pre-submit check in the deep lane that refuses to finish the outline when no assessment backs any declared path. The problem would then be found at authoring time instead of by the Q-Gate.

## Evidence

3-outline Q-Gate finding 8eb2e9 in plan-39-module-readmes-and-adrs, resolved taken_into_account after 91 assessments were recorded afterwards.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-39-module-readmes-and-adrs-007.md` from plan plan-39-module-readmes-and-adrs (PLAN-39, #53; Claude Code)
