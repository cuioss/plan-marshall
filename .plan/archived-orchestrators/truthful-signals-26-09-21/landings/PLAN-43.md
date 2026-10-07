# Landing Analysis: PLAN-43 — `architecture find` Confident False Negatives Past the Elision Horizon

epic: truthful-signals
workstream: WS-01
pr: 989

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against
> ground truth. Operator landing narrative TRUSTED; deliverable fidelity corroborated against the
> merged commit `9d992f7bc` on `origin/main`.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — truthful-negative reader-boundary seam (find + which-module self-scan / truncation) | shipped-as-specified | Operator narrative + PR #989 title "truthful find/which-module past elision cap"; `_resolve_module_inventory` self-scans an in-scope elided category from the worktree, degrades to `truncated:true` + `elided[]` when self-scan impossible (ADR-009 fail-closed). Matches spec D1's shape (a)+(b), (a) as fix, (b) as floor. |
| D2 — raise cap + strided sample | shipped-modified | Spec D3 said "raise/parameterize"; landed as `_FILES_CATEGORY_CAP` 500→2000 + strided sample replacing `paths[:100]` byte-sorted. Modification is within spec latitude (D3 was explicitly a palliative, "a cap only moves the horizon" — the truthful negative from D1 is the real fix). |
| D3 — regression test, over-cap category cannot produce a silent zero | shipped-as-specified | `test_find_confident_negative.py`, three arms, stated to fail against pre-fix code — pins the truthful-negative invariant, not the cap value, exactly as spec D4 required. |
| (unplanned) simplify-pass removal of speculative process-lifetime memo | added-unplanned | finalize-step-simplify removed a self-scan memo that can never hit in the single-invocation CLI model; a net simplification, not scope creep. |

Spec deliverable numbering (D1–D4) collapsed to the report's 3 because spec D2 (implement in find
AND which-module) and D1 (choose shape) landed as one seam. No deliverable dropped.

## Metrics and Anomalies

- Tokens: ~2M (record-metrics).
- Duration: 1h42m worked.
- Anomalies: two argparse slips during finalize (`manage-status --field`, `architecture --plan-id`)
  logged `script_failure` markers; both self-corrected, operator judged them not lesson-worthy. They
  inflate the run's Signal-Gate script-failure count without reflecting a plan or tool defect. Noted
  as a process observation, not a defect (see Follow-Ups).

## Routing and Merge Behavior

- Review: automatic-review 0 comments (both bots). review-retrospective "nothing to compare."
- CI/merge: all checks green; squash-merge via merge queue; rebased onto origin/main; worktree
  removed, working tree clean. deploy-target → v0.1.1199, 10 bundles synced, executor regenerated.
- Collisions: none. PLAN-43 ran concurrently with PLAN-41/42/44; no rebase conflict or re-verify
  signal reported against any of them — the surface-disjointness pairing held.

## Reconciliation Actions

- [x] status.json `plans[]` entry updated — PLAN-43 → shipped, pr=989, landing=landings/PLAN-43.md
- [x] epic.md queue reconciled from status.json
- [x] Open Defect / Watch (4) "architecture-find confident false negative" retired — resolved by this landing
- [x] resume_anchor updated
- [x] START-HERE block regenerated

## Follow-Ups

- Durable lesson `2026-07-23-01-001` captures the general principle (a reader over a capped/elided
  store must never treat the sample as the whole — self-scan or surface `truncated`). This is the
  reusable residue; no orchestrator action owed.
- Process observation (NOT staged): finalize-phase argparse slips inflate the script-failure
  Signal-Gate count with self-corrected, non-defect noise. Related to the standing
  `recipe-fix-argparse-rejection` surface. Recorded as a watch, not a plan — it is a recurring-noise
  signal, and one instance is below the bar for a staged fix.
