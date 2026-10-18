envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:50Z

component=plan-marshall:execution-context
category=anti-pattern
created=2026-10-18

# Give leaves a sanctioned in-file and sibling-repo search when Grep is denied

## Context

Grep was denied to every dispatched leaf of plan-20-job-runner. Most leaves used `architecture search --content`, but at least four (code-review rounds 2 and 5, functional-review round 1, the fix of finding 207f76) fell back to Bash `grep` and flagged the deviation themselves. The code-review leaf of round 4 also could not check the sibling documentation repository at all, because the inventory does not walk it and Bash grep is forbidden.

## Root cause

The execution-context contract names `architecture search --content` as the fallback, but it covers only the module-attributed inventory of the current repository. Enumerating phrases across a whole file set, or searching a sibling checkout the project's link checker spans, has no sanctioned path, so leaves either break the rule or silently narrow their coverage.

## Proposed action

Either grant Grep to review and fix leaves, or extend the sanctioned search to the sibling paths a project declares (here `../plan-marshall-documentation`) and document a multi-phrase sweep form, so no leaf needs Bash grep.

## Evidence

- aspect: permission_prompt_analysis - Grep denied throughout; 4 leaves used Bash grep
- aspect: chat_history_analysis - code-review round 5: "I used architecture search --content and a bash grep, once ... This contradicts the instruction"; round 4: "Bash grep was not usable for the sibling documentation repository"
