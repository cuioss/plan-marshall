envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:50:46Z

component=plan-marshall:phase-3-outline
category=improvement
confidence=medium
source_plan=dual-homed-hook-install-renders-identically
source_aspects=artifact_consistency,outline_vs_shipped,request_result_alignment

# An operator-approved mid-run scope addition must return to the outline

## Context

During finalize, the pre-push module-tests gate came back red on exactly one test — a `manage-architecture` subprocess timeout (30s budget against a 24-57s verb), 19,525 others passing. The operator was asked how to record it and answered "Fix the test budget in this plan". The fix landed in `test/plan-marshall/manage-architecture/test_architecture_input_validation.py`, which shipped in the merge.

The approval was correct and the fix was correct. What did not happen is the write-back: the file entered `references.json` but never entered `solution_outline.md`. Two first-party checks now report the approved change as a defect signature:

- `check-artifact-consistency` — `affected_files_exact_match: warn`, `references_only[1]` naming that path
- `check-outline-vs-shipped` — `touched_but_unassessed: 2 of 9`, that path among them

## Root cause

There are two write paths into a plan's declared surface: the outline (authored, assessed, Q-Gated) and the operator answer applied in-flight (recorded in `references.json` only). The second has no return path to the first, so an approved scope change is indistinguishable from undeclared drift to every downstream reader.

## Proposed action

When an operator answer expands the footprint mid-run, append the path to the owning deliverable's declared file list with an explicit provenance annotation (e.g. `(operator-approved, {phase}, {timestamp})`), so the declared surface stays the record of what the plan was authorised to touch. Downstream checks can then distinguish an approved addition from drift instead of reporting both as a set mismatch.

Alternatively — and more cheaply — have `check-artifact-consistency` and `check-outline-vs-shipped` read a provenance marker on `references.json` entries, so an approved addition is reported as such rather than as `references_only` / `touched_but_unassessed`.

## Evidence

- Session transcript (reduced), operator-decision turn: "Fix the test budget in this plan"
- aspect: artifact_consistency — `affected_files_exact_match.references_only[0] = test/plan-marshall/manage-architecture/test_architecture_input_validation.py`
- aspect: outline_vs_shipped — `touched_but_unassessed.count: 2 of 9`, same path a member
- `manage-solution-outline list-deliverables`: 8 declared paths across 2 deliverables; the realized footprint is 9
