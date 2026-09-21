envelope_version=1
sender_type=plan
sender_id=plan-07-session-identity
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-18T20:15:52Z

# Quality-gate auto-fix churn widens the realized footprint beyond declared files

## Context

The plan-07-session-identity realized footprint held 26 paths against 8 declared: 18 test files under test/plan-marshall/workflow-integration-github|gitlab from quality-gate auto-fix churn (ruff check --fix + format), not feature drift. Absorbed with no follow-up owed.

## Root cause

Auto-fix churn lands in the same footprint the outline-vs-shipped comparison measures, so every plan with gate churn reports touched_but_unassessed noise.

## Proposed action

Consider attributing quality-gate churn separately in the footprint comparison so declared-vs-shipped stays a feature signal.

## Evidence

- aspect: outline-vs-shipped — touched_but_unassessed 26 of 26 realized_footprint_paths
- aspect: artifact_consistency — affected_files_recall 100%, exact-match forwarded to manifest
- plan: plan-07-session-identity, PR #1530
