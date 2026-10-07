envelope_version=1
sender_type=plan
sender_id=plan-truth-103
epic=truthful-signals
kind=candidate-lesson
created=2026-09-13T12:08:10Z

# Candidate lesson: the fix for a mirrored set re-introduced a mirrored set one layer down — and only an ALTERNATION of internal gate and external reviewer caught it

**Source plan**: plan-truth-103 (PR #1475)
**Evidence**: first-party PR-comment findings `8c4832` (CodeRabbit round 1, **Major**, reviewed commit `11acd645`) and `3c3297` (CodeRabbit round 3, reviewed commit `8081dfbf`), with this plan's own triage text on `3c3297` naming the causal link.
**Dedup note**: not among the 10 findings already routed this run. The two underlying comments were both remediated in-run; what is recorded here is the RELATIONSHIP between them, which neither comment states.

## The chain

1. **Round 1 — `8c4832` (Major).** CodeRabbit: "Guard the complete `resolve_settings_arg` caller set." Four test methods in `TestSharedSeamCallSites` **hand-listed** the current callers (`cmd_apply_fixes`, `cmd_consolidate`, `cmd_ensure_wildcards`, `cmd_apply_project_step_permissions`); a new caller would bypass coverage silently. Cited the repository convention directly: mirrored sets must be derived or guarded.

2. **The fix (TASK-006).** An AST-derived structural test: parse `permission_fix.py` for every function calling `resolve_settings_arg`, parse `TestSharedSeamCallSites` for the handlers it covers, assert the derived population is non-empty (non-vacuity), then assert subset. Correct, and it closed the reported defect. Worth noting the triage also verified the hand-list was *accurate at the time* — "nothing automatic was keeping it correct, which is exactly your point."

3. **Round 3 — `3c3297`.** CodeRabbit: `_OPERATION_ARGUMENT_KIND` is a **second operation registry**; a newly published operation fails in `_argument_for` instead of running through the ownership test. Derive from `PERMISSION_FIX_OPERATIONS` instead.

4. **The link, stated first-party in this plan's own triage of `3c3297`:** *"it was introduced by the round-1 fix on this same PR for the identical archetype, so the fix for a mirrored set re-introduced one a layer down."*

## Why this is worth a lesson

The archetype is already known to this repo (`DERIVE completeness, never assert it`; "treat a hardcoded list that must mirror a set defined elsewhere as a defect unless it is derived at build or run time"). What is **new** is the propagation shape and the detection requirement:

- The defect was re-introduced **by the remediation of its own archetype**, one abstraction layer down. Knowing the rule did not prevent re-committing the violation while applying the rule — the author's attention was on the *reported* mirrored set, and the new mirror was scaffolding created to fix it.
- It crossed the **internal-gate / external-reviewer boundary**. Round 1 was external; the fix passed the internal self-review tier; round 3 was external again. A single review pass could not have seen it (the round-3 defect did not exist at round 1), and a single internal gate pass could not have seen it either (the internal tier had already accepted the fix). Only the alternation caught it.

## The operational consequence

This is the concrete argument for the finding already routed as `265638` (one shared `loop_back_iteration` counter lets the self-review tier starve the external-review tier) — and it should be read alongside it. On this run the self-review chain consumed all 5 admissible iterations *before* the wait-region producers ran; the round-3 external finding recorded here is exactly the class that would then have been refused a loop-back. Had the cap not been raised 5→10 under an explicit operator standing order, the mirrored registry introduced by the round-1 fix would have shipped.

## The terminating move (consistent with the sibling candidate on deletion)

The fix for `3c3297` was **deletion, not correction**: "The map encodes exactly one fact, so it goes entirely" — `_argument_for` branches on the single named `protect-path` exception instead, and the parity assertion goes with it, because there is no longer a second set to compare. One addition was load-bearing: the parity assertion had also been the only guarantee that the POSITIVE half of the ownership test still fired, so the non-vacuity test was extended to assert the deny-writing operation is a **member of** `PERMISSION_FIX_OPERATIONS` — a query against the authoritative set, not a second copy of it. That distinction (query the source; never mirror it) is the generalizable residue.
