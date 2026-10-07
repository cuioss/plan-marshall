# WS-06: `interaction_mode` — the persisted experience knob

epic: operator-ux

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-06-interaction-mode.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Introduce `interaction_mode` (`basic` | `advanced` | `expert`) as one persisted preference
that scales how much plan-marshall asks and explains, chosen at `/marshall-steward` and
changeable later. The knob is deliberately the LAST workstream: it is a multiplier on
behaviour the other five establish, and a knob layered over unfixed defaults would only add a
dimension to the confusion. The workstream closes when a user can pick a mode once and see the
system's prompting and output volume change coherently across the whole lifecycle.

## Scope

- In scope: the `interaction_mode` field in `marshal.json` and its validator; the
  `manage-config` read/write surface; the `/marshall-steward` menu entry that sets it on first
  run and on later invocation; the mapping from each mode to the behaviours the other
  workstreams established — how much context a prompt carries, how much output a phase
  boundary emits, and whether a borderline gate asks or proceeds.
- Out of scope: the *defaults themselves* — WS-01 through WS-05 set the baseline, and this
  knob modulates it; renaming or touching `skill_domains.active_profiles`, which is an
  unrelated work-activity concept that merely shares the English word "profile".

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-09-interaction-mode | staged | `interaction_mode` config field, steward menu entry, and the mode-to-behaviour mapping |

## Sequencing and Surface Notes

- **Last in the epic.** Depends on PLAN-04 (the gate census tells the mode what there is to
  modulate), PLAN-06 and PLAN-07 (the vocabulary and volume rules are what `basic` dials up).
- Collides with WS-02 and WS-05 on `wizard-flow.md` / `menu-configuration.md`, and with WS-01
  and WS-02 on `_config_defaults.py`. Sequence.
- **`expert` must not become an escape hatch that re-enables the domain prompt.** WS-01's fix
  is a correctness fix — the detector had the information all along — and re-exposing it as an
  expert preference would reframe a defect as a taste. If an expert wants to override a
  resolved domain set, the existing `--domain-override` is the right surface.
- The three-mode enum is the operator's chosen shape. Guard against it growing a fourth value
  per complaint; a mode that means "everything the previous mode did, plus one exception" is a
  sign the underlying default is wrong and belongs in WS-01–WS-05.
