envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:09Z

component=plan-marshall:phase-6-finalize
category=bug
title=Keep hand-filed sonar-issue raw_input inside the finding schema

# Keep hand-filed sonar-issue raw_input inside the finding schema

## Context

With no Sonar credential configured, sonar-roundtrip filed two sonar-issue findings by hand (`manage-findings add --type sonar-issue`) and quarantined the Sonar issue key under `raw_input.issue_key`. The unified triage's batched `manage-findings ingest` rejected both because the finding schema has `additionalProperties: false` on `raw_input`, and set them to `resolution: rejected`. Triage re-resolved them to `fixed` by hand.

## Root cause

The sonar-roundtrip fallback path does not state which `raw_input` keys the finding schema admits, and ingest maps a schema rejection to `resolution: rejected` — which, with `do_transition: true`, would be posted to Sonar as `falsepositive`.

## Proposed action

State the admissible `raw_input` keys on the sonar-roundtrip manual-filing path (or extend the schema with `issue_key`), and make an ingest schema rejection a distinct non-dismissing state rather than `rejected`.

## Evidence

- aspect: chat_history_analysis — triage report: "Both were rejected by manage-findings ingest because their raw_input carries an extra key, issue_key"
- aspect: llm_to_script_opportunities — the plain-HTTP read and hand-filing ran in all 3 sonar-roundtrip firings
- plan: plan-v2-132-coverage-parser-hardening, findings 466add and af6339
