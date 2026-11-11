envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4-v2
epic=lessons-routing
kind=candidate-lesson
created=2026-11-07T20:34:27Z

component=plan-marshall:phase-3-outline
category=bug
confidence=high
source_plan=plan-v2-93-http-tests-annotations

# Freeze every line of a wrapped success-criterion bullet in the snapshot

## Context

In plan-v2-93 the outline froze 16 success criteria at the 3-outline transition. The functional-review leaf found that the criteria snapshot kept only the first line of each wrapped bullet, so six outline criteria had no row of their own (1.C2, 2.C3, 8.C2, 8.C3, 8.C4, 9.C2). The leaf graded them by hand and folded their evidence into surviving rows; the mechanical gate never graded them. Criterion 8.C4 (Sonar quality gate) was among the lost ones.

## Root cause

The snapshot parser treats a bullet as a single physical line and drops continuation lines, so a criterion that wraps is truncated or merged.

## Proposed action

Parse a criterion bullet up to the next bullet or heading (continuation lines included) when freezing the snapshot, and add a test that a wrapped bullet yields one full criterion. Have the functional-review validator report the outline-vs-snapshot criterion count so a mismatch is visible.

## Evidence

- chat-history-analysis: functional-review report, "The criteria snapshot froze only the first line of each wrapped bullet ... Six outline criteria have no row of their own"
- status.json: criteria_integrity.snapshot_frozen true with 16 criteria checked, against more criteria in the outline
- request-result-alignment: residuals on D6 and D8 graded by hand
