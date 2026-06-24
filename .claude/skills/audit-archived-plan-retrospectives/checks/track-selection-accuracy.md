# Check: track-selection-accuracy

Reconstructs each archived plan's counterfactual "correct" planning track from
its realized signals and compares it against the track the plan actually ran,
emitting an `OVER-TRACKED` / `UNDER-TRACKED` / `correct` verdict. The
deterministic comparison lives in `scripts/audit.py`; this sub-document is the
interpretation guide.

The counterfactual reuses the LIVE routing logic: the check imports
`evaluate_signals_pure` and the S5 `_request_is_concrete` helper from
`_cmd_planning_lane.py` (the `plan-marshall:manage-status` planning-lane router)
and scores the recorded signals through them. No routing threshold is duplicated
in the audit — the audit and the live router stay in lockstep by construction.

## Inputs the check reads

**Actual track (what the plan ran):**

- `status.json::metadata.planning_lane` — the lane the router resolved at
  phase-1-init (`light` | `deep`).
- `references.json::track` — the coarser track recorded for the plan
  (`simple` | `complex`). When absent, the actual track is derived from the
  recorded lane (`deep ⇒ complex`, `light ⇒ simple`).

**Counterfactual signals (fed to `evaluate_signals_pure`):**

- `scope_estimate` — `references.json::scope_estimate` (S2).
- `change_type` — `status.json::metadata.change_type` (S3).
- `compatibility` — `plan.phase-2-refine.compatibility` from the project
  `marshal.json` (S4); project-level, read once per corpus scan.
- `plan_source` — the plan's recorded source (`status.json::metadata.plan_source`,
  surfaced as `recipe_key`) (S1).
- `request_concrete` — re-derived from the archived `request.md` body via the
  imported `_request_is_concrete` (the S5 anchor regexes: file path, fenced code
  block, `python3 .plan/execute-script.py` CLI, or `manage-*` notation).

## Verdict mapping

The check compares the actual lane against the counterfactual lane
`evaluate_signals_pure` returns (`light` | `deep`):

| Verdict | Condition |
|---------|-----------|
| `OVER-TRACKED` | The plan ran `deep`/`complex`, but the realized signals score the counterfactual `light` — heavier ceremony than the signals warranted. |
| `UNDER-TRACKED` | The plan ran `light`/`simple`, but the realized signals score the counterfactual `deep` — lighter ceremony than the signals warranted. |
| `correct` | The actual lane matches the counterfactual lane. |
| `not_recorded` | The plan recorded neither a `planning_lane` nor a `track` — nothing to compare. |
| `no_routing_logic` | The live planning-lane router could not be imported — the check degrades rather than raising. |

## Emitted columns

```text
rows[N]{plan_id,actual_lane,actual_track,counterfactual_lane,verdict}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `actual_lane` | The recorded `planning_lane` (`light` / `deep`; empty when unset). |
| `actual_track` | The recorded `references.json::track`, or the lane-derived track when `track` is absent. |
| `counterfactual_lane` | The lane `evaluate_signals_pure` returns for the realized signals (empty for the degrade verdicts). |
| `verdict` | `OVER-TRACKED` / `UNDER-TRACKED` / `correct` / `not_recorded` / `no_routing_logic`. |

## How the orchestrator interprets the rows

- **`correct`** — the plan ran the track the signals warranted; no action.
- **`OVER-TRACKED`** — the plan ran heavier than its signals justified (deep/complex
  where the counterfactual is light). Surface it as a ceremony-overhead signal:
  a plan that runs the deep lane on a request that scores light pays the
  discovery cost for no benefit.
- **`UNDER-TRACKED`** — the plan ran lighter than its signals warranted (light/simple
  where the counterfactual is deep). Surface it as a routing-miss signal: a
  request whose signals score deep but that ran light may have under-discovered.
- **`not_recorded` / `no_routing_logic`** — informational; the verdict could not be
  computed (missing lane/track, or the router was unavailable). Treat as "no
  data", never as "correct".
- Recurring OVER-/UNDER-TRACKED verdicts across the corpus are a candidate
  systemic signal — the router's thresholds may be mis-calibrated. Cross-read
  with the recurring-pattern detector before filing a lesson.

## Critical rules

- The script is the single source of truth for the routing logic: it imports
  `evaluate_signals_pure` from `_cmd_planning_lane.py` rather than re-deriving any
  threshold. Do not re-score the signals in chat.
- This check is read-only; it never edits `.plan/` files.
