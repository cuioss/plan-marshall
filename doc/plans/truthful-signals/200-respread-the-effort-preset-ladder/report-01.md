# Run report — 200-respread-the-effort-preset-ladder (run 01)

**Date (UTC):** 2026-08-12    **Branch:** `claude/respread-effort-preset-ladder-tbc523` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (working contract — loaded first)
- `plan-marshall:ref-code-quality` (read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (read from bundle path)

Domain skills to load when implementation proceeds (Python production/tests, adoc): `pm-dev-python:python-core`, `pm-dev-python:pytest-testing`, `pm-documents:ref-asciidoc`, `plan-marshall:persona-implementer`.

## D1 GATE — claim verification (mutates nothing)

Every claim in the plan's claim-label table was treated as `HYPOTHESIS` and re-derived from source.

| Claim | Verdict | Evidence |
|---|---|---|
| Nine-slot values total 23 / 30 / 34 | **CONFIRMED** | Re-summed from `effort_presets.py`: ECONOMIC 2+3+3+3+2+3+2+3+2=23; BALANCED 3+3+4+3+4+3+3+3+4=30; HIGH_END 3+4+4+4+4+4+3+4+4=34 |
| `high-end` matches `balanced` in 5/9 slots, never exceeds level-4 | **CONFIRMED** | Matches: default, phase-3-outline, phase-5-execute.default, phase-6-finalize.default, phase-6-finalize.post-run-review. Max level across all high-end slots = level-4 |
| Module reserves level-5 against preset use | **CONFIRMED (with nuance)** | Reserved in **prose** only — module docstring, `HIGH_END` attribute docstring, and `_DESCRIPTIONS['high-end']` all state *"level-5 (opus, high) is reserved for explicit per-phase opt-in … never a preset default."* BUT `RESERVED_LEVELS = ()` is **empty** (validator forbids nothing), and its own comment says *"level-7 is the current top tier … so presets may reference it."* Levels 5/6/7 are all in `ALLOWED_LEVELS`. So the reservation is a design convention, not a hard constraint, and it is internally contradicted by the `RESERVED_LEVELS` comment — itself a latent doc-contract-divergence |
| Only two high-end slots below level-4, so +2 is the max bump under the reservation | **CONFIRMED** | Only `default` (3) and `phase-6-finalize.default` (3) are below 4; all-4 total = 36 = +2 |
| Wizard recognises a preset by deep-equality match | **CONFIRMED** | `marshall-steward/standards/effort-menu.md` Step 1: identify preset "by deep-equality against `EffortPresets.ECONOMIC/.BALANCED/.HIGH_END`"; non-match → `Current: custom (manually edited)`. Match set walks `EffortPresets.all_names()` |
| Retired-key migration precedent exists in defaults-sync | **CONFIRMED** | `_cmd_sync_defaults.py`: `RETIRED_STEP_KEY_RENAMES` (old→canonical dict, walked by `_migrate_retired_step_keys`, marked `# SHIM(A)`); plus a second `_RUN_AT_ALL_TO_LANE` migration. This is the "old→new mapped explicitly" shape D2 points to |
| Population is 7 sites | **REFUTED** | Single-token sample undercounts. Sweep across `high-end` + `apply-preset`/`EffortPresets`/`effort_presets` + `economic`/`balanced` yields a larger set, and critically **includes `_config_defaults.py`** (a value-consumer via literal mirror) and **excludes** the retrospective script. Full D4 population re-derived at implementation time |
| Retrospective routing-verification script reasons about preset identity | **REFUTED** | `check-routing-decisions.py` reasons about `execution_profile` **posture** and the `no_code_delta` prune predicate — orthogonal to effort presets. No reference to any preset name or level value (the only `economic` grep hit is the substring "token-**economic**s"). A re-spread does **not** change its verdicts on past runs. Same for `routing-decision-verification.md` |
| Per-phase seeded defaults are literal copies, not derived | **CONFIRMED** | `_config_defaults.py` hardcodes the balanced values (`DEFAULT_PLAN_EFFORT='level-3'`; phase-2 level-3, phase-3 level-4, phase-4 level-3, phase-5 {default:level-4, verification-feedback:level-3}, phase-6 {default:level-3, verification-feedback:level-3, post-run-review:level-4}), each commented "balanced-preset baseline" and said to "mirror" `EffortPresets.BALANCED` — **not** imported. They drift the moment the balanced payload changes |
| No other consumer depends on exact payload values | **PARTIAL** | Value-consumers found: `effort_presets.py` (source), `_config_defaults.py` (literal mirror). Writer `_cmd_effort.py` reads values dynamically (no hardcoding). Wizard match is prose over `EffortPresets`. Tests assert values. `coverage_presets.py` / `finalize_step_presets.py` are unrelated (different preset families) |

### Level table (from `effort-levels.md`), for the cost decision

| Level | Model / effort | Note |
|---|---|---|
| level-3 | sonnet / high | Sonnet's top |
| level-4 | opus / medium | **today's high-end ceiling** |
| level-5 | opus / high | Opus's standard top — **the reserved tier** |
| level-6 | opus / xhigh | alias-capability-gated (build refuses if alias lacks `xhigh`) |
| level-7 | fable / max | alias-capability-gated (build refuses if alias lacks `max`) |

⇒ level-6/7 are **unsafe as preset defaults** (silent canonical fallback when the alias can't emit them), so **level-5 is the practical ceiling** for a "genuinely high-end" preset. The fork is level-4 vs level-5.

## D1 GATE — the four questions

1. **May high-end use level-5?** ⛔ Load-bearing, and a cost/intensity policy choice. **Not self-decided.** Escalated to the operator (reachable interactive session — permitted by `cloud-plan-lane` § "Rules that outrank convenience"). See below.
2. **Which "default" is meant?** **Settled by reasoning.** The plan's spread table row `default` = the `default:` key **inside each payload** (one of the nine slots); the request says nothing about changing which preset a new project ships with, and that is explicitly out-of-scope. So "default" = the per-payload `default:` level. (Collateral: because `_config_defaults.py` literally mirrors balanced, the new-project baseline tracks whatever the middle rung becomes — handled in D3/D4, not a change of "which preset is default".)
3. **New middle name + target spread number.** Escalated with Q1 (coupled).
4. **Cheapest tier gets more expensive.** ✅ **Disclosed:** old economic (23) → new economic (= old balanced, 30) is a **~30% floor increase for every project currently on `economic`**, the preset a cost-sensitive user deliberately chose. This is a real, intended consequence of the request.

## Escalation to operator (Step-D1 fork)

The run is an interactive session with a reachable operator. Per the lane contract, a STOP CONDITION with an autonomous fallback **may** be escalated rather than defaulted (`AskUserQuestion`).

**Q1 — High-end ceiling (level-5 policy):** _"How high may the new high-end preset go? … lifting the prose reservation so it can use level-5 (opus/high) …"_
→ **Answer: Allow level-5.** The reservation is lifted for high-end; the reservation comment and every doc restating it are updated in lock-step. Full D2–D5 proceeds.

**Q2 — Tier naming:** _"… how should the tiers be named?"_
→ **Answer: Keep economic / balanced / high-end.** Values re-spread under the existing names; D2 migration recognises old-shaped configs and offers re-apply.

The STOP CONDITION is therefore **not** taken (operator lifted the blocker); the run proceeds through D3–D5.

## Locked ladder (D1 target as NUMBERS)

The re-spread target is **totals 30 / 36 / 41** (economic / balanced / high-end), with **per-slot monotonicity** (economic ≤ balanced ≤ high-end in every one of the nine slots) and **every adjacent gap ≥ 5** (original was +7 / +4; new is +6 / +5). The level-5 footprint is **0 / 3 / 5** slots.

| Slot | economic | balanced | high-end |
|---|---|---|---|
| default | 3 | 4 | 4 |
| phase-2-refine | 3 | 4 | 5 |
| phase-3-outline | 4 | 5 | 5 |
| phase-4-plan | 3 | 4 | 5 |
| phase-5-execute.default | 4 | 5 | 5 |
| phase-5-execute.verification-feedback | 3 | 3 | 4 |
| phase-6-finalize.default | 3 | 3 | 4 |
| phase-6-finalize.verification-feedback | 3 | 3 | 4 |
| phase-6-finalize.post-run-review | 4 | 5 | 5 |
| **Total** | **30** | **36** | **41** |

`economic` is exactly today's `balanced` payload (satisfying "move economic up to today's balanced values"). `high-end` lifts every analytical/execution/review slot to level-5 (opus/high), keeping triage at level-4; `default` stays level-4 (level-6/7 excluded as alias-gated). `balanced` is the even midpoint.

**Seeded-defaults decision (`_config_defaults.py`):** the literal per-phase defaults (= old balanced = 30) are **kept at their current values** — a fresh project's cost is unchanged (out-of-scope forbids an unprompted new-project cost increase). Because those values now equal the **`economic`** preset, the "balanced-preset baseline" comments are corrected to `economic`, and a guard test asserts the seeded shape deep-equals `EffortPresets.ECONOMIC`. Net effect: a fresh project's wizard display changes `balanced → economic` with **no cost change**.

