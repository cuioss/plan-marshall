envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T18:33:32Z

# Proposed lesson: add bulk resolve for superseded pending findings

Component: plan-marshall:manage-findings
Category: improvement
Confidence: high

## Context

The pre-merge findings gate blocked the merge-queue enqueue on 38 stale intermediate test-failure findings from superseded builds. Each was resolved individually as fixed with green-CI evidence before the gate passed.

## Root cause

No bulk operation exists for resolving a filtered pending set with one shared rationale, so a superseded population costs one call per finding.

## Proposed action

Add a manage-findings bulk-resolve verb taking a type plus pending filter and a single shared detail string, emitting one decision-log line for the batch.

## Evidence

- aspect: llm-to-script-opportunities — 38-repetition candidate, low complexity
- aspect: manifest-decisions — pre_merge_gate refused with blocking_findings_present until the batch cleared

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `plan-44-static-verifier-rule-gaps-004.md` from plan plan-44-static-verifier-rule-gaps (PLAN-44, #38; opencode)
