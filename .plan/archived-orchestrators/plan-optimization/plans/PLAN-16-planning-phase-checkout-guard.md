# PLAN-16: planning-phase-checkout-guard

epic: plan-optimization
workstream: WS-08

> Staged plan spec. Promoted from the planning-phase-edits-main watch (n=2: lesson 17-001 #920,
> lesson `2026-07-18-13-002` PLAN-05). Re-ground the exact lesson IDs + guard site at outline.

## Objective

Add a proactive guard so a planning-phase (phase-3-outline / phase-4-plan) or dispatched-leaf agent
cannot silently edit the MAIN checkout — a correctness violation (source mutation outside the plan's
worktree) that recurred this epic. Both occurrences (lesson 17-001 at #920; `2026-07-18-13-002` at
PLAN-05, where a phase-4 re-dispatch edited the actual doc on main and was reverted) were caught
REACTIVELY. The invariant already exists in prose (`phase3-outline never mutates source`,
`phase2-refine never implements`); this plan makes it enforced, not just documented.

## Deliverables

### D1 — enforce the planning-phase no-main-mutation invariant

Add a Q-Gate / topology guard (or a phase-boundary post-condition) that detects a planning-phase or
dispatched-leaf agent writing to the MAIN checkout and blocks or loudly flags it before it lands —
rather than relying on a later reactive revert. **Confirm at outline** whether the right seam is a
Q-Gate check, a phase-3/4 post-condition (clean-main assertion), or an execution-context
main-vs-worktree write guard. **Acceptance:** a planning-phase edit of a main-checkout source file is
blocked/flagged at the phase boundary; a legitimate worktree edit is unaffected. Regression test.

## Out of scope / do NOT expand
- The leaf-validator sub-dispatch topology (PLAN-03, shipped).
- The footprint build-gating (PLAN-11).

## Absorbs
- Lessons 17-001 (#920) and `2026-07-18-13-002` (PLAN-05) — the leaf/planning-edits-MAIN class.

## Expected Surface
- phase-3-outline / phase-4-plan phase-boundary post-condition, and/or a Q-Gate check
- `execution-context` main-vs-worktree write boundary
- tests: planning-phase main-edit blocked; worktree edit allowed

## Dependencies and Sequencing
- Depends on: none.
- Overlaps with: in-flight PLAN-11 (both touch phase-4) — coordinate/rebase if they overlap on the
  phase-4 surface. Disjoint from the rest.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-16-planning-phase-checkout-guard.md"
```

## Status Trail
- plan_marshall_plan_id: planning-phase-checkout-guard
- pr: #945 (squash-merged to main via merge queue, 2026-07-19)
- landing: landings/PLAN-16.md
- status: SHIPPED — D1 delivered both halves: runtime clean-main assertions at planning-outline.md Step 2c (outline_contract_violation) / Step 4b (plan_contract_violation), and the plugin-doctor _analyze_phase2_refine_contract.py analyzer generalized to emit outline-contract-violation / plan-contract-violation for phase-3-outline / phase-4-plan (+ provenance rows + regression tests). Seam confirmed at outline = (b) phase-boundary clean-main assertion + static plugin-doctor complement (rejected Q-Gate and execution-context write-guard). Absorbs lesson 17-001's planning-phase class; the phase-5 occurrence (2026-07-17-17-001) remains out of scope (retained). Two self-review Boy-Scout fixes folded in (stale _doctor_analysis.py comment + missing phase-4-plan enforcement bullet).
