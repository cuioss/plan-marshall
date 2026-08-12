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

## Deliverables

| Deliverable | What was done | Commit | Verification |
|---|---|---|---|
| **D1 GATE** | All HYPOTHESIS claims re-derived (table above); 4 questions settled/escalated; STOP CONDITION lifted by operator | `4a78fdf` (report) | Mutates nothing; claim table is the artifact |
| **D2 MIGRATION** | `LEGACY_PRESETS` registry (SHIM(A)-marked) + `EffortPresets.identify()` + `reconstruct_effort_payload()` + new `manage-config effort identify` verb (wired in `manage-config.py`) + wizard `effort-menu.md` Step 1/2 rewrite to call it. Pre-respread economic (23) / high-end (34) shapes recognised as `previous-ladder` with a re-apply offer instead of silent `custom` reclassification. Deterministic script result replaces LLM deep-equality eyeball (truthful-signals) | `3ce2258` | identify unit tests + round-trip + **genuinely-old-config** tests (both old economic & old high-end shapes) + end-to-end CLI test |
| **D3 Apply ladder** | Three payloads re-spread to 30/36/41; module + attribute docstrings, `_DESCRIPTIONS`, and the level-5 reservation prose updated in lock-step (reservation re-anchored to the alias-gated level-6/7) | `3ce2258` | value-assertion tests updated; monotonic + spread tests green |
| **D4 Docs** | Full population re-derived (below). Updated: `effort-roles.md` (no false value — left as-is, verified), `api-reference.md` (apply-preset success payload + new `identify` verb section + verb table), `effort-menu.md` (deterministic legacy-aware Step 1/2), `manage-config/SKILL.md` (Canonical invocations: `effort identify`), `doc/user/efforts.adoc` (preset table + **fixed false "No slot is level-5"** + identify note). `_config_defaults.py` comments balanced→economic. **Consumer script verdict:** `check-routing-decisions.py` does NOT depend on preset identity — no retrospective verdicts on past runs change (see Findings) | `3ce2258` | plugin-doctor clean; grep sweep for stale reservation prose clean |
| **D5 Tests** | Spread assertion (30/36/41 + gaps ≥5), **seen red against the old ladder**; inverted level-5 guard (high-end must reach level-5, no preset uses level-6/7); identify unit/round-trip/legacy/CLI tests; seeded-defaults deep-equality guard | `3ce2258`, `216ebdc` | all green in `./pw verify` |

### D4 derived population (re-derived across all three names + apply verb + class/module ids)

**Sites that restated tier values/names and were updated (6):** `effort_presets.py`, `_config_defaults.py`, `api-reference.md`, `effort-menu.md`, `manage-config/SKILL.md`, `doc/user/efforts.adoc`. **Plus 3 test files.**

**Sites in the population that needed NO change (verified, not assumed):** `effort-roles.md` (names presets + "monotonic ladder" — still true), `execution-context.adoc` (generic cross-refs only), `effort-variants.md` (level enum only), `plan-marshall/SKILL.md` / `marshall-steward/SKILL.md` / `wizard-flow.md` / `menu-configuration.md` (no name+value restatement), `manage-logging/SKILL.md` (generic "balanced preset" log example), and the two REFUTED retrospective sites (`check-routing-decisions.py`, `routing-decision-verification.md`).

**Count:** derived population ≈ 15 sites naming a preset/verb; **9 files changed** (6 docs/code + 3 tests). A count of files touched is a volume, not coverage — the coverage claim is: every site restating a tier *value* was updated, and every site naming a preset was inspected and either updated or verified still-true.

## Build gate

`git diff --name-only origin/main...HEAD -- '*.py'` → non-empty (production + tests). Build takes its **full path**.

- `./pw quality-gate` → **0 issues** (mypy production 395 files, ruff, SPDX, plugin-doctor marketplace-wide; `coverage: COMPLETE`).
- `./pw verify` → **`=== verify: SUCCESS ===`**, **19168 passed, 14 skipped** (adds mypy(test) 713 files + whole-tree module-tests). One iteration: an initial `test-compile` surfaced 2 mypy errors in the new tests (a `no-any-return` on the dynamically-loaded handler and an `arg-type` on the deliberate malformed-input guard test), both fixed in `216ebdc`, after which verify is clean.

## Findings

| Source | Finding | Disposition |
|---|---|---|
| D1 verification | The level-5 "reservation" is prose-only: `RESERVED_LEVELS=()` empty and its comment says presets "may reference level-7" — internally contradicting the docstrings. | Fixed by the re-spread: level-5 is now a deliberate preset default; reservation prose re-anchored to the genuinely alias-gated level-6/7. Contradiction resolved. |
| D4 consumer-script verdict | `check-routing-decisions.py` reasons about `execution_profile` **posture** and the `no_code_delta` prune predicate, **not** preset names/values (the only `economic` grep hit is substring "token-**economic**s"). | **The re-spread changes NO retrospective verdicts on past runs.** The plan's "highest-consequence unknown" is refuted with evidence. No edit needed to that script or `routing-decision-verification.md`. |
| D1 cost disclosure | Old economic (23) → new economic (30) is a ~30% floor increase for every project on `economic`. | Disclosed to operator (Q4); operator accepted via the "Allow level-5" decision. Seeded new-project defaults kept at current values to avoid an *additional* unprompted increase. |
| build test-compile | 2 mypy errors in new tests (no-any-return, arg-type). | Fixed in `216ebdc`; verify re-run clean. |
| **Verification sub-agent (Step 6)** | **GAP — doc-contract-divergence archetype:** `marshall-steward/references/wizard-flow.md:247` still said the init effort seed mirrors the **`balanced`** preset. After the re-spread the seed equals **`economic`** (spread 30); balanced is now 36. My run-01 coverage note wrongly listed wizard-flow.md as clean (my grep searched name+level on one line; this claim names the preset without a level). | **Fixed** in `936347b` (`balanced`→`economic`). Followed by a broader tree-wide sweep (preset name adjacent to seed/mirror/baseline/expanded/default-level) — no other stale claim survives. Re-dispatched the sub-agent to confirm. |

### Step 6 sub-agent — clean verdicts (what it examined)

The sub-agent independently re-derived and PASSED 5 of 6 areas: D3 ladder values (re-summed 30/36/41, per-slot monotonic, economic == former balanced, no level-6/7, high-end reaches level-5); D2 migration (`identify()` + `_LEGACY_PRESETS` hold the *actual* old economic-23/high-end-34 shapes, old balanced-30 handled by current-match-first, full CLI wiring, well-formed SHIM); seeded defaults (values unchanged, comments corrected, guard test binds seed to ECONOMIC); consumer-script verdict (**`check-routing-decisions.py` does NOT depend on preset identity** — independently confirmed, no past-run verdicts change); and D5 tests (spread assertion is concrete-and-red-against-old, level-5 guard inverted not deleted, identify coverage complete incl. genuinely-old-config). The single GAP (wizard-flow.md) is fixed above.

