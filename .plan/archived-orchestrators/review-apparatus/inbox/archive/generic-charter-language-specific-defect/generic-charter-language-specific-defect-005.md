envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T16:51:06Z

# A request-declared write-boundary exclusion is prose with no gate behind it

component: plan-marshall:phase-5-execute
category: improvement
confidence: medium
source_aspects: request_result_alignment

## Context

The request named PLAN-PR-013 as the owner of `automatic-review/review_completeness.py` and its currency test, and stated of that surface: "No file overlap; it stays untouched here." This plan nevertheless modified `test/plan-marshall/automatic-review/test_review_completeness.py`, which landed in `f5493b437`.

The reasoning behind the edit is sound and was recorded at the time. Deliverable 4's outline prediction — that "every registry-consuming module passes unedited" — was falsified at execution: two cases in that module asserted the pre-widening record directly. The leaf held the line on the registry change and migrated the two cases under the update-tests-not-implementation rule with `compatibility=breaking`, adding a negative control so the widening reads as an enumeration rather than a blanket admission (decision.log 2026-08-09T09:01:41Z). As an engineering call this is the right one.

What is missing is the reconciliation. The decision log records *why the outline prediction was wrong*; nothing records *that a request-declared exclusion was crossed*, and nothing routes that fact to the sibling plan whose surface it is. PLAN-PR-013 will next touch a file this plan has already changed, with no signal that it happened.

## Root cause

An `Exclusions` clause in a request is prose. Nothing extracts it into a checkable set, so no phase-5 or phase-6 step can notice when the realized footprint intersects it. The declared exclusion and the realized footprint are both machine-readable; only the comparison is missing.

## Proposed action

1. Extract request `Exclusions` / write-boundary clauses that name concrete paths into a checkable set at outline time, and compare the realized footprint against it at the same point the coverage comparison runs.
2. On an intersection, do not block — the crossing here was correct — but require an explicit reconciliation record, and in an orchestrated run emit a `finding` message to the epic naming the sibling plan whose declared surface was entered.
3. Epic-specific follow-up: PLAN-PR-013's scope should be re-read against `f5493b437` before it is launched, since two of its test cases have already been migrated.

## Evidence

- aspect: request_result_alignment — `scope_creep` entry for `test/plan-marshall/automatic-review/test_review_completeness.py`; write-boundary finding
- request.md § Dependencies and Sequencing — "Adjacent to: PLAN-PR-013 … No file overlap; it stays untouched here"
- decision.log 2026-08-09T09:01:41Z — the falsified D4 prediction and the migration rationale
- landed commit `f5493b437` — the file is in the merged footprint
