# WS-04: Module-Budget Campaign

epic: test-quality

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-04-module-budget-campaign.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Drive **B1** — the epic's one structural rule, the 400-line module budget — to zero, honestly. This is
the workstream nobody reached: every reduction plan sequenced its split deliverable last, for the sound
reason that fixture hoisting changes which modules are over budget, and every run exhausted its budget
before getting there. The split is therefore no longer a reduction plan's deliverable at all. It is a
**campaign**: one slice per run, measured against the budget rather than against a line target. The
workstream closes when the rule's count reaches zero over a population that includes every module in
the tree it governs — not only the collected ones.

## Scope

- In scope: splitting over-budget `test_*.py` modules by behaviour cluster, one reduction slice per
  run; the campaign's own apparatus (the fidelity differ, the duplication detector, the banner
  attribution checker); and the budget rule's own definition where it fails to measure what it names.
- Out of scope: reducing a slice by any means other than splitting (WS-02's); the skip and wall-clock
  instruments (WS-05's); flipping `test-module-line-budget` to `severity: error`, which is a policy
  decision with a named owner in WS-03; raising the 400-line budget itself.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-100-module-budget-campaign | landed (run 1 of 7) | Run 1 split slice `050`, creating 66 `_{domain}_fixtures.py` helpers. **Runs 2–7 are unrun** and are re-staged as PLAN-140 |
| PLAN-105-every-module-counts-and-the-campaign-can-finish | staged | Closes run 1's leftovers: the three modules over budget by one class alone, the helper modules the rule cannot see, the uncommitted instruments, and ~691 inert lint suppressions |
| PLAN-140-module-budget-campaign-runs-2-7 | staged | The remaining six campaign runs, re-sized against a freshly derived per-slice attribution |

## Sequencing and Surface Notes

- **`105` runs before `100`'s run 2.** Its D3 and D4 change what a campaign run measures and what it
  must otherwise rebuild by hand; running them in the other order means run 2 re-derives an instrument
  from prose, which is exactly the failure `105` exists to prevent.
- **`100` takes a slice only after that slice's plan has landed.** All six have, so the constraint is
  now satisfied for every row.
- **`110` is best run before the campaign continues**, because the campaign is what it exists to watch:
  a campaign run adds several hundred modules, each re-running its own import preamble at collection.
- **`105` reaches into two other workstreams' surfaces and says so.** § D3 edits one analyzer in
  WS-03's exclusive tree; § D7 sweeps ~250 files across it; § D4 places instruments in WS-01's
  `test/_shared/`, shared with `110`. Each carries a halting concurrency check, and D7 is taken **last**
  so a collision costs one commit rather than the run.
- **`105` carries seven deliverables**, above the epic's split guard. The rationale for proceeding
  unsplit is recorded as an epic decision.
- **The campaign's own metric is currently blind to a growing part of the tree.**
  `analyze_test_module_line_budget` filters on `_is_collected_module`, so no helper module is ever
  measured — and a split's most available move is to shift bulk into a helper. Until `105` § D3 lands,
  a falling count is not evidence that lines left the tree.
