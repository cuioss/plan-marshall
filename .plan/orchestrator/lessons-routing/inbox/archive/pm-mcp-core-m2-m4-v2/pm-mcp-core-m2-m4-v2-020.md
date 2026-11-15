envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-12T17:47:10Z

component=plan-marshall:phase-3-outline
category=improvement
title=Declare spec-mandated test rewrites under Tests to remove

# Declare spec-mandated test rewrites under Tests to remove

## Context

The plan spec required rewriting three existing tests: `JacocoReportParserTest.refusesAnInternalSubsetBehindAComment` (the internal-subset refusal is gone), and `CoveragePercentagesTest.readsAnEmptyPopulationAsZero` and `refusesANonFiniteRate` (0/0 is now absent; rates parse as text). The outline described the rewrites in prose but declared no `**Tests to remove:**` entries, so `review_support test-integrity` raised blocking `weakened_test` rows, the functional-review verifier declined (`may_close: false`), and finalize had to escalate to the operator, who accepted the three rewrites.

## Root cause

The outline step does not convert a spec instruction to rewrite or replace an existing test into the structured removal declaration that test-integrity checks against.

## Proposed action

When a deliverable rewrites or renames an existing test (its prose names the old test), require the outline to list it under `Tests to remove:` with its replacement, so test-integrity accepts it without an operator round-trip.

## Evidence

- aspect: chat_history_analysis — operator decision "Fix wording, then accept both rewrites (recommended)"
- status.metadata.accepted_test_removals — 3 identities accepted
- decision.log 88af49 — "Verifier declined; may_close=false"
- plan: plan-v2-132-coverage-parser-hardening
