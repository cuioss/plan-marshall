# PLAN-176: Module-Budget Campaign, Run 2 (Slice 040)

epic: test-quality
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-176-module-budget-campaign-run-2-slice-040.md` and is queued in
> the epic `status.json` `plans[]` field. The orchestrator EMITS the command below; it
> never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
>
> ⛔ **Scope is exactly one campaign run.** This spec replaces the run-2 row of
> `PLAN-140-module-budget-campaign-runs-2-7.md` (parked, superseded by per-run specs —
> one spec per run, each shippable alone, per the self-containment rule). Runs 3–7 are
> staged just-in-time after this run lands; they are not this plan's scope and this plan
> does not gate on them.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode): process compliance is mandatory, not advisory.

## Objective

Drive **B1** — the 400-line module budget — down inside slice `040` (delivery
pipeline) and land the result as its own PR: re-derive the slice's over-budget
population at dispatch, split over-budget modules by behaviour cluster using the
committed instruments, and prove nothing was lost. Done when the slice's
over-budget count is lower than the dispatched baseline with identical fidelity
multisets, both orders passing, and every figure reported with the command that
produced it.

## Deliverables

1. **D1 — Re-derive before acting.** ⛔ **Gating.** Derive this run's slice membership
   from PLAN-040's own `## Expected Surface`, and its over-budget population from the
   doctor's own sweep at dispatch HEAD. Compare against the campaign lead (57 at HEAD
   `2cd1a19c`, twelve `test/` commits have landed since — the figure is stale on
   arrival) and **report the delta rather than adopting either figure silently**.
   *Done when:* the slice's directory list, its over-budget module list and its count
   are each recorded with the command that produced them, and any disagreement with
   the lead is stated.
2. **D2 — Split by behaviour cluster, never by arbitrary halves, and never a class.**
   `test_{unit}_{cluster}.py`. ⛔ **A class is never split** — a module whose whole
   content is one class under the 500-line ceiling is **exempt** by PLAN-105 § D2 and
   must not be touched; a class *above* that ceiling is reported, not split.
   ⛔ **Use PLAN-105's committed instruments** — the fidelity differ, the duplication
   detector and the banner attribution checker — rather than rebuilding them from
   prose.    *Done when:* the slice's over-budget count is reported before and after;
   every module split is named with its resulting modules; and no class has been
   split. A wall that forces a hoist rather than a split is **reported as such**,
   not banked as a split (run 1's M32 residue).
   ⛔ **Splitter discipline (lesson `2026-09-17-15-001`, slice-040 precedent,
   archived at `archive/lessons/2026-09-17-15-001.md`):** exactly one cluster file
   performs any `load_script_module` registration — siblings import the registered
   object (acyclic), never re-register; `@parametrize` travels with its test;
   fixtures consumed by contract modules are kept in every cluster file; prune
   imports per file for F401. String-target patches against a re-registered name
   resolve to a stale object and fail everywhere but the last-imported file.
3. **D3 — Prove nothing was lost.** The `Class::test` multiset and the comment/code-line
   counts must be identical across the move, **both ends derived by one instrument**.
   ⛔ A before/after pair whose two sides were produced by different scripts, or one of
   whose sides was quoted from an earlier run, is a defect regardless of whether the
   numbers look right. *Done when:* the differ reports both sides with its definition
   printed, and the multisets are identical.
4. **D4 — Order-independence.** Hoisting changes what a module binds at import time. Run
   the affected directories in **default and reverse** directory order.
   *Done when:* the affected directories pass in both orders, and the result is
   recorded. (Strict serial reverse-order is not runnable on this host — record the
   parallel form explicitly rather than claiming the serial signal.)
5. **D5 — Report the measured deltas.** The slice's budget count before and after; the
   fidelity multisets; the duplication figure at both refs with the detector's
   definition printed; the reverse-order result; the collected item count; the skipped
   count; and the wall-clock with its population named.
   *Done when:* the report carries every figure with the command that produced it.

## Claim Labels

- OBSERVED: this run owns slice `040` (delivery pipeline) and is the next campaign
  row — read at `plans/PLAN-140-module-budget-campaign-runs-2-7.md` § `The Six Remaining Runs` (run 2 → slice `040`, prerequisites met) and the epic queue (all ordering prerequisites landed).
- HYPOTHESIS: the slice's over-budget population at dispatch — confirm/refute at
  `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py` § `analyze_subprocess_pythonpath` (verify-at-outline; the whole-tree count has risen at every measurement, so any transcribed figure is a lead D1 re-derives).
- OBSERVED: PLAN-105's instruments exist and D2 must use them — read at
  `landings/PLAN-105.md` (fidelity differ, duplication detector, banner attribution
  checker committed by #1407).
- OBSERVED: run-sized PRs forfeit automated review past file-count ceilings — read at
  `landings/PLAN-100.md:52-53` (309 files, both reviewers refused at 100/300). Keep
  this run's PR carved small; the carving decision is the operator's at dispatch.
- HYPOTHESIS: the Expected Surface below is this run's footprint — confirm/refute at
  `plans/PLAN-040-delivery-pipeline-test-reduction.md` § `Expected Surface`
  (verify-at-outline; D1 re-derives the row from the owning plan's spec and reports
  the delta).

## Expected Surface

- HYPOTHESIS: `test/plan-marshall/automatic-review/` — slice `040` delivery-pipeline coverage (verify-at-outline; D1 re-derives from the owning spec)
- HYPOTHESIS: `test/plan-marshall/manage-ci-artifacts/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-5-execute/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/tools-integration-ci/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-shared/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-git/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-github/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-gitlab/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-integration-sonar/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-permission-web/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/workflow-pr-doctor/` — slice `040` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/test_phase_6_finalize_step_id_consistency.py` — slice `040` file (verify-at-outline)

## Dependencies and Sequencing

- Depends on: PLAN-030, PLAN-040, PLAN-060, PLAN-070, PLAN-080, PLAN-105, PLAN-110 (all
  landed — every ordering prerequisite is met).
- Overlaps with: none live (flight line empty at stage time; N=1 sequential).
- Adjacent to: PLAN-155's slice (`060` runtime substrate) and PLAN-150's slice (`070`)
  under the same `test/plan-marshall/` root — nearby surfaces this run does not touch.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-176-module-budget-campaign-run-2-slice-040.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
