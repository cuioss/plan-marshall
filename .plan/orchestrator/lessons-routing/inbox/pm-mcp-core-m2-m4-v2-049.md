envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-21T09:47:09Z

component=plan-marshall:phase-3-outline
category=improvement
created=2026-11-21
bundle=plan-marshall
title=Declare the ADR 026 baseline files when a spec adds enum test fixtures

# Declare the ADR 026 baseline files when a spec adds enum test fixtures

## Context

Every new enum test fixture in pm-mcp-core (ReasonFixtures, ReasonVerifyPrimitives, ReasonPrimitives) tripped the hand-written-double scan, so execute had to amend ADR 026 and both `hand-written-doubles.txt` baselines, none of which the outline declared. Together with a reflective record test and the watch count, 11 realized files were undeclared; the functional-review verifier refused one round because only 7 were graded.

## Root cause

The outline treated the ADR 026 scan as invisible: an enum that implements `PrimitiveOutcome`/`OutcomeReason` cannot be an EasyMock double, so the closed list always needs an amendment.

## Proposed action

In staged specs of this epic that add enum (or other non-mockable) test fixtures, list `doc/adr/026-...adoc` and the module's `src/test/resources/hand-written-doubles.txt` under the deliverable's affected files, and list reflective tests of a record whose components change (e.g. `WorkflowEngineRecordsTest`).

## Evidence

- aspect: request_result_alignment - 11 files outside every declared surface, 4 of them from the ADR 026 scan and the reflective test
- aspect: artifact_consistency / manifest_decisions - references_only 11, rule M6 declared_vs_realized_set fail
- aspect: chat_history_analysis - verifier refusal "unrequested list is incomplete: 11 undeclared files, only 7 entered"
