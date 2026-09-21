# PLAN-20: execution-accounting-integrity

epic: plan-optimization
workstream: WS-10

> Staged plan spec. Promoted from TWO high-recurrence watches this epic tracked to n=3 and n=5
> respectively. Both are "the pipeline reports/records a state it has not earned" at the execution
> layer. Re-ground the exact lesson IDs, call sites, and current step-record shape at outline.

## Objective

Make phase-5/phase-6 execution accounting honest in two places where it demonstrably is not:
a leaf reports a task verified without running the tests that task could break, and finalize records a
step under a key that does not match the manifest `step_id`, so the pipeline cannot reliably find its
own bookkeeping. Both recurred repeatedly across this epic despite existing prose and existing gates.

## Deliverables

### D1 — leaf per-task verification must run the tests it can break

**Watch: `2026-07-18-22-001`, n=3** (PLAN-14 #942, PLAN-16 #945, PLAN-13 #950 — three independent
confirmations). A phase-5 leaf's per-task verification runs **mypy + ruff + compile but NOT pytest**, so
contract-breaking regressions escape the leaf and are caught only later — at the finalize whole-tree gate
(PLAN-14 #942), at bot review, or not at all. PLAN-14 fixed the *finalize gate*; the leaf is still the
hole. **Evidence it matters:** PLAN-14's own leaf shipped 2 real correctness defects to bot review;
PLAN-13's whole-tree run caught a D5 base-class test under-scope the leaf missed.

**Fix:** bring the tests a task can break into that task's per-task verification scope. **Confirm the
seam at outline** — candidates: (a) resolve the task's test scope from its footprint (the
`resolve-test-scope` seam PLAN-14 #942 already shipped is the obvious reuse — check it first, do NOT
build a parallel one), (b) compose a pytest step into the leaf's verification when the footprint is
buildable, (c) a phase-5 post-condition. **Respect the execution-tier/timeout constraints** — a leaf must
not background a long build (`feedback_orchestrator_owns_long_builds`, #893/#912); scope-resolution is
what keeps this cheap. **Acceptance:** a task whose change breaks a test in its own resolved scope FAILS
at the leaf, not at finalize; a docs-only/no-python-footprint task runs no pytest and is not slowed.
Regression test.

### D2 — finalize step-record key must match the manifest `step_id`

**Watch: `step_record_mismatched_key`, n=5** (PLAN-11 #938 automatic-review; PLAN-16 #945 mark-step-done;
merged into lesson `2026-07-13-12-003`). `project:`/`default:`-prefixed finalize steps record under a key
that mismatches the manifest `step_id`, so `mark-step-done` / `assert-step-recorded` disagree with the
manifest. n=5 is the highest recurrence count in the epic. **Note:** plan-16 #885 already shipped
step-key hygiene (compose fail-loud + retired-key rename) — this is the *prefixed-step* residual it did
not cover, NOT a redo. **Fix:** make the record key resolution canonical for prefixed steps.
**Acceptance:** a `project:`/`default:`-prefixed step records under a key `assert-step-recorded` resolves
against the manifest; a mismatch fails LOUD at compose/record time rather than being silently tolerated.
Regression test covering both prefix forms.

### D3 — structural guard so neither regresses

Where D1/D2 land, add the structural check that stops a NEW step or leaf from regressing into the same
shape (a plugin-doctor-style rule or a compose-time assertion — mirror the pattern PLAN-16 #945 used for
its contract violations, and PLAN-13 #950 D4 used for fail-closed writes). **Acceptance:** a newly-added
prefixed step with a mismatched key, or a leaf verification that omits an in-footprint test scope, is
caught structurally rather than by a reviewer or by recurrence. **Confirm at outline whether ONE guard
covers both or two are needed** — do not force a shared abstraction if the shapes differ.

## Out of scope / do NOT expand
- The finalize whole-tree divergence gate (PLAN-14 #942, shipped) — D1 is the LEAF half, not a redo.
- `manage-locks` staleness (PLAN-22) and the review barrier (PLAN-21) — sibling plans, disjoint surfaces.
- The marshalld-contaminates-build-queue-unit-tests isolation defect (lesson `2026-07-19-22-001`) — that
  is the plan-server epic's build-server surface. If D1's pytest scoping trips over it, STOP and note it;
  do not fix marshalld here.

## Absorbs
- Watch "Phase-5 leaf verification runs mypy+ruff+compile but NOT pytest" (lesson `2026-07-18-22-001`, n=3) → D1.
- Watch "`step_record_mismatched_key`" (lesson `2026-07-13-12-003`, n=5) → D2.

## Expected Surface
- phase-5-execute per-task verification composition + execution-manifest verification steps (D1)
- `pyproject_build resolve-test-scope` (PLAN-14 #942 seam — REUSE, verify before extending) (D1)
- `manage-status` `mark-step-done` / `assert-step-recorded` + manifest `step_id` resolution (D2)
- plugin-doctor analyzer or compose-time assertion (D3)
- tests: leaf-fails-on-in-scope-test-break; docs-only-runs-no-pytest; prefixed-step-key-round-trip;
  structural-guard-catches-new-violation

## Dependencies and Sequencing
- Depends on: none. PLAN-14 #942 (`resolve-test-scope`) and plan-16 #885 (step-key hygiene) are shipped
  preconditions to BUILD ON, not to redo.
- Surface-disjoint from PLAN-21 and PLAN-22 (startable in parallel) and from in-flight PLAN-18.

## Size / split guard
3 deliverables — comfortably under the ~6 presumption. **Deliberately keeps D1 and D2 together**: split
apart, both halves land on the execution-manifest surface and would have to be sequenced, costing the
parallelism that makes PLAN-21/22 concurrent. If outline finds D1 alone exceeds a plan's worth (the test-
scope seam proving deeper than the PLAN-14 reuse suggests), split D2+D3 out as a follow-up and record it
as an epic decision.

## Hand-Off Command
```text
/plan-marshall task="implement .plan/local/orchestrator/plan-optimization/plans/PLAN-20-execution-accounting-integrity.md"
```

## Status Trail
- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when landings/PLAN-20.md is recorded}
