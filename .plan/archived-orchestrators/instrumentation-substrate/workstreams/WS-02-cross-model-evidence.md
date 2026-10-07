# WS-02: Cross-model evidence

epic: instrumentation-substrate

> Charter document for one workstream. Lives at `workstreams/WS-02-cross-model-evidence.md` and is
> tracked in the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The corpus is calibrated against one model it does not name and ships byte-identical to a fleet it
cannot vary for. The generator translates *vocabulary* — what a tool is called, how a skill is loaded
— and cannot vary *how emphatically an instruction is stated* or *how much verification scaffolding a
workflow carries*, because those travel in prose. This workstream settles two questions in order:
whether a calibration axis should exist at all, and what a behavioural signal on a non-Claude runtime
would have to look like before any answer to the first is actionable.

It closes when a corpus edit's effect on a runtime nobody currently measures is a number, or when the
epic has recorded a deliberate, dated decision that it will not be.

## Scope

- In scope: the calibration-axis decision and its ADR; the design and first implementation of a
  cross-model evaluation signal; the isolation discipline that keeps the model-under-test the single
  varying term; the naming of the flaws in the prior art that must not be reproduced.
- Out of scope: ⛔ **any edit to instruction wording in the shared corpus.** That is the action this
  workstream exists to gate, and no plan staged here may perform it. Also out of scope: the
  `antigravity` target's own delivery, which this workstream neither owns nor holds.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-03-calibration-axis-decision | staged | Decide, while a third runtime is still in flight, whether the generator grows a model/tier axis or deliberately declines one. Decision + ADR, not implementation. |
| PLAN-04-cross-model-eval-signal | staged | Build the behavioural signal on a non-Claude runtime, with the prior art's four named flaws designed out. |

## Sequencing and Surface Notes

- PLAN-03 is the time-sensitive row in the whole epic: the cost of retrofitting a calibration axis
  rises with every target that ships without one, and with every consumer repository pinned to their
  output. It is cheapest now and never cheaper again.
- PLAN-04 depends on PLAN-03's **decision**, not merely on its landing. A refused axis does not cancel
  PLAN-04 — it changes what PLAN-04 is for, from a calibration instrument to a regression tripwire.
  Re-read PLAN-04's objective against PLAN-03's recorded outcome before emitting its command.
- ⚠ The variance axis is **model**, not target. One `opencode` target hosts several models, so
  paragraph-level `targets:` scoping and a per-target mapping layer are both insufficient by
  construction. Any design that keys on target is refuted before it is built.
- Surfaces are adjacent but not identical: PLAN-03 touches `doc/adr/` and the generator's
  documentation; PLAN-04 touches a new evaluation surface. They are still sequenced, because PLAN-04's
  shape is not determined until PLAN-03 has resolved.
