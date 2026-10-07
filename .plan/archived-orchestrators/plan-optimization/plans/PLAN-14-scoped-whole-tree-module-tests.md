# PLAN-14: scoped-whole-tree-module-tests

epic: plan-optimization
workstream: WS-04

> Staged plan spec. Promoted from the scoped-vs-whole-tree watch (source: PLAN-08 #934, lesson
> `2026-07-18-22-001`). Re-ground citations at outline.

## Objective

Close the finalize-gate blind spot where a per-task SCOPED quality-gate / module-tests run passes
while a whole-tree run would fail. On PLAN-08 the scoped gate passed but whole-bundle module-tests
caught a real 33-failure regression. This is the SAME "match the authority" class **PLAN-02 #927 D1
fixed for `plugin-doctor`** (scoped-green vs CI-whole-tree-red) — now observed for the module-tests /
quality-gate. Extend that discipline to the module-tests gate.

## Deliverables

### D1 — module-tests / quality-gate gate must match the whole-tree authority (or warn on divergence)

Mirror PLAN-02 D1's resolution for `plugin-doctor`: either run the finalize module-tests gate
whole-tree to match what CI (and a fresh checkout) sees, OR warn loudly when a scoped-green result
could diverge from a whole-tree run. **Do NOT blanket-force whole-tree if it's cost-prohibitive** —
PLAN-02 chose the match-or-warn shape; confirm the same trade-off at outline. **Acceptance:** a change
that is scoped-green but whole-tree-red (like PLAN-08's 33-failure regression) is caught or explicitly
warned at finalize, not first at CI / a later whole-tree run. Regression test with a scoped-green /
whole-tree-red fixture.

## Out of scope / do NOT expand
- The pre-merge comment barrier (PLAN-10, same WS-04).
- `plugin-doctor` scoping (PLAN-02 #927 already fixed — the reference behavior).

## Absorbs
- Lesson `2026-07-18-22-001` (scoped-gate blind spot).

## Expected Surface
- phase-6-finalize `pre-push-quality-gate` / module-tests gate step + its scope resolution
- `build-pyproject` / `build-maven` module-tests scoping (which module set the gate runs)
- tests: scoped-green / whole-tree-red fixture

## Dependencies and Sequencing
- Depends on: none.
- Overlaps with: PLAN-10 (WS-04) touches phase-6 finalize but a different step (comment barrier vs
  quality-gate) — mostly disjoint; rebase if both touch phase-6 SKILL. Disjoint from the rest.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-14-scoped-whole-tree-module-tests.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-14.md is recorded}
