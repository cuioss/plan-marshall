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
in the audit — the audit and the live router stay in lockstep by construction. The
counterfactual verdict is **era-aware around the #854 light-lane carve-out** (see
below): because `evaluate_signals_pure` is the current post-#854 router, an
OVER-TRACKED verdict attributable to the carve-out is annotated as era-relative
rather than counted as an absolute routing miss.

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

## Era-awareness: the #854 light-lane carve-out

`evaluate_signals_pure` is the LIVE router, so its narrow-and-concrete carve-out
(#854) is the CURRENT scoring: a request that is BOTH narrowly scoped
(`scope_estimate ∈ {surgical, single_module}`) AND concretely specified
(`request_concrete`) stays `light` even when its `change_type` is generative or its
`compatibility` is `breaking` — the S3/S4 co-firing the carve-out suppresses. Under
the PRE-#854 router that same co-firing forced `deep`. A plan that ran `deep`
before #854 shipped is therefore scored `OVER-TRACKED` here only BECAUSE of the
carve-out: its deep run was consistent with the router in force when it ran.

The check flags this by appending a `:carve_out` suffix to the row's `era` stamp
(the CHECK_ERA boundary `#854`) whenever an OVER-TRACKED verdict's light
counterfactual is attributable to the carve-out — i.e. the plan is narrow-scoped
AND concrete AND would otherwise have scored deep on S3/S4. The attribution is
derived from the router's OWN constants (`_NARROW_SCOPE_ESTIMATES`,
`_DEEP_CHANGE_TYPES`, imported, never duplicated), so no threshold is copied. An
`era` of `#854:carve_out` marks the over-tracking as ERA-RELATIVE (a
post-#854-only verdict), distinct from a plain `#854` era stamp on a verdict that
holds under any era.

## Emitted columns

```text
rows[N]{plan_id,actual_lane,actual_track,counterfactual_lane,verdict,era}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The scanned plan's directory basename. |
| `actual_lane` | The recorded `planning_lane` (`light` / `deep`; empty when unset). |
| `actual_track` | The recorded `references.json::track`, or the lane-derived track when `track` is absent. |
| `counterfactual_lane` | The lane `evaluate_signals_pure` returns for the realized signals (empty for the degrade verdicts). |
| `verdict` | `OVER-TRACKED` / `UNDER-TRACKED` / `correct` / `not_recorded` / `no_routing_logic`. |
| `era` | The CHECK_ERA boundary (`#854`), suffixed `:carve_out` when an OVER-TRACKED verdict is attributable to the #854 light-lane carve-out (era-relative). Empty for the degrade verdicts. |

## How the orchestrator interprets the rows

- **`correct`** — the plan ran the track the signals warranted; no action.
- **`OVER-TRACKED`** — the plan ran heavier than its signals justified (deep/complex
  where the counterfactual is light). Surface it as a ceremony-overhead signal:
  a plan that runs the deep lane on a request that scores light pays the
  discovery cost for no benefit. **Read the `era` column first**: an
  `era: #854:carve_out` row is ERA-RELATIVE — the light counterfactual holds only
  under the post-#854 carve-out, so a plan that ran BEFORE #854 shipped was correct
  for its era and MUST NOT be counted as a routing mistake the planner could have
  avoided at the time. Treat carve-out-attributed over-tracking as evidence the
  carve-out is now doing its job, not as a per-plan miss. A plain `era: #854`
  OVER-TRACKED row (no `:carve_out` suffix) is a genuine over-track that holds
  under any era.
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
- The #854 carve-out attribution reads the router's OWN constants
  (`_NARROW_SCOPE_ESTIMATES`, `_DEEP_CHANGE_TYPES`) via `_routing_const` — it
  duplicates no threshold and degrades to a plain (non-carve-out) `era` stamp when
  the router renames a constant. If the carve-out's inputs change, the change flows
  through the imported router automatically.
- This check is read-only; it never edits `.plan/` files.
