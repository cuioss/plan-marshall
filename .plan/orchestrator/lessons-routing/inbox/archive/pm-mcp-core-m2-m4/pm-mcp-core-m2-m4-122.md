envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-12T05:32:01Z

# Cross-repository deliverables: declared ../ paths diverge from where the work is done, and the footprint cannot see them

Source: plan-retrospective of static-verifier-and-fuzzer (artifact-consistency and manifest-decisions aspects, rule M6 `declared_vs_realized_set` = fail); execute envelope 1 hand-back.

## What happened

Deliverables 1, 5, 6 and 7 targeted the documentation repository and were declared as `../plan-marshall-documentation/...` paths (the operator kept that form at outline). At execute time the `../plan-marshall-documentation` checkout was on another session's unpushed branch (`feature/runtime-lifecycle`), so the leaf rightly created a separate worktree `plan-marshall-documentation-static-verifier-and-fuzzer` and did the work there. The declared paths therefore never named the files that changed.

Consequences:

- The realized footprint covers this repository only. All 9 documentation paths land in `outline_only`, recall drops to 75%, and rule M6 reports `fail` although the work shipped (plan-marshall-documentation PR #34).
- q-gate-validation could not check those paths either: they are outside the architecture inventory.
- Task text kept pointing at `../` paths that the leaves had to remember to redirect.

## Candidate rule / fix

Give a plan a first-class notion of a companion repository: declare the sibling repo plus its own worktree/branch at outline, let execute record the realized companion worktree, and have the footprint resolver and rule M6 grade companion paths against that worktree (or mark them `companion_unmeasured` rather than `outline_only`). Owner: plan-marshall `phase-3-outline` / `manage-references` footprint / `plan-retrospective` M6.

- Origin: pm-mcp-core epic pm-mcp-core-m2-m4, inbox `static-verifier-and-fuzzer-009.md` from plan static-verifier-and-fuzzer (PLAN-10, #32)
