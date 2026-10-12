envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-11T20:54:38Z

# Documentation deliverables must enumerate every doc file they write, not defer to a trace matrix

## Observation

Deliverable 11 (documentation in the sibling repository plan-marshall-documentation) said concept, developer and user topic documents "are created or extended ... with their indexes" and that every dangling reference is re-pointed, leaving the exact files to the trace matrix. Affected files listed only six paths. The declared write-set therefore omitted files the deliverable would write, so sync-affected-files and the phase-4 declared-set closure could not see them. The fix pass enumerated all nine doc pages with absolute paths and replaced the open-ended re-pointing clause by "headings and anchors stay".

## Rule

A deliverable's Affected files must be closed: name every file it will create or modify, including index pages, at outline time. An open-ended clause ("and every referrer is re-pointed") is under-coverage; either enumerate the referrers or constrain the change so no unlisted file is written.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `runtime-lifecycle-003.md` from plan runtime-lifecycle (PLAN-08, #29)
