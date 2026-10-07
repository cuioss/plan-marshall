# WS-02: Autonomy gate defaults

epic: operator-ux

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-autonomy-defaults.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Settle the lifecycle autonomy gates on one principle: **`plan_without_asking` is the single
deliberate human checkpoint, and every other transition proceeds by default.** Three of the
five `*_without_asking` knobs already default `true`, so this workstream is narrower than it
first appears — it flips `loop_back_without_asking`, re-examines the step-owned
`final_merge_without_asking`, and produces a census establishing that no *other* pause gate
was missed. The workstream closes when a routine plan runs start to finish with exactly one
user checkpoint, and the census names every gate that can still stop it.

## Scope

- In scope: the flat `plan.*` autonomy knobs in `_config_defaults.py`; the step-owned
  `final_merge_without_asking` under `default:branch-cleanup`; the `gate_mode` gates
  (`deep_lane`, `escalation`, `revalidation`) and `lane_selection` insofar as they *pause*;
  the wizard copy that presents them (`wizard-flow.md`, `menu-configuration.md`); the
  reference tables in `manage-config/SKILL.md` and `marshal-json-reference.md`.
- Out of scope: the domain prompt (WS-01 — it is a detector gap, not an autonomy knob); the
  content or wording of prompts that legitimately survive (WS-03, WS-05); the orchestrator's
  own `auto_emit` knob, which is a separate tier and not part of the user's complaint.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-04-autonomy-gate-defaults | staged | Flip `loop_back_without_asking`, audit `final_merge_without_asking`, publish the pause-gate census |

## Sequencing and Surface Notes

- Collides with WS-01 on `manage-config/SKILL.md` and `marshal-json-reference.md`, and with
  WS-05 on `menu-configuration.md` / `wizard-flow.md`. Sequence against both.
- **The `max_iterations` guard is the load-bearing reason the flip is safe** and must be
  verified still to hold at HEAD before the default changes — the pause is being retired in
  favour of a bound that already exists, not in favour of nothing.
- The census deliverable is what makes this workstream closable. Without it, "we flipped the
  knobs we knew about" is indistinguishable from "no pause gate remains".
