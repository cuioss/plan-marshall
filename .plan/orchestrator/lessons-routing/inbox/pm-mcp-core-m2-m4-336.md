envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:50Z

component=plan-marshall:workflow-integration-sonar
category=bug
created=2026-10-18

# Skip Sonar issues whose key already has a triaged finding

## Context

At HEAD b494a52 of plan-20-job-runner, `fetch_findings --pr 92` filed two "new" pending findings, e826b9 (java:S1117) and 648763 (java:S6539). Both carry the same Sonar keys as 44d47c (triaged fixed by TASK-25) and 77cd42 (triaged suppressed). The leaf left them pending, where they count against the findings gate. Separately, PR 92 was in conflict at the time, so Sonar was still reporting the issues at lines from before the fix commits.

## Root cause

The producer dedupes by finding hash, not by Sonar issue key, so an issue that Sonar re-reports on a stale analysis comes back as a fresh pending finding.

## Proposed action

In `fetch_findings`, look up the Sonar key in the store first; when a finding with that key is already resolved, skip it or file it pre-resolved with a pointer to the earlier disposition. Also report `mergeable: conflicting` from `ci pr view` in the step result, because a conflicting PR means the analysis may describe an older tree.

## Evidence

- aspect: chat_history_analysis - sonar-roundtrip FIND at b494a52: "Neither of the two filed issues is new: both are Sonar issues the store already holds"; "PR #92 is in conflict"
- aspect: llm_to_script_opportunities - dedupe-by-key proposed as a low-complexity script change
