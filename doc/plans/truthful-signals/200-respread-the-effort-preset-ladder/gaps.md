# Gaps — 200-respread-the-effort-preset-ladder

**Source:** verification.md (same directory)   **Open items:** 5

The ladder values, the migration recogniser, and every test guard are correct — verified by executing
the module and by two mutation checks that both went red. Every gap below is a documentation-surface
miss: one stale statement that inverts the shipped policy inside the plan's own primary file, and four
sites where the new `effort identify` verb (or the mechanism change it caused) was not carried through.

## G1 — Delete the "presets may reference level-7" clause from the `RESERVED_LEVELS` comment

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py:86-88` — the comment above `RESERVED_LEVELS`
- **What is wrong:** the comment reads *"No effort levels are currently reserved. `level-7` is the current top tier (resolves to fable, max — sits above Opus) **so presets may reference it**."* After the re-spread, four other sites say the opposite: the module docstring at `:37-42` (*"`level-6`/`level-7` are NOT used as preset defaults … stay reserved for explicit per-phase opt-in"*), `_DESCRIPTIONS['high-end']` at `:295` (*"level-6/level-7 stay opt-in only (alias-gated)"*), `doc/user/efforts.adoc:67` (*"`level-6`/`level-7` are **not** used by any preset"*), and — executably — `test/plan-marshall/plan-marshall/test_effort_presets.py::test_high_end_reaches_level_5_but_never_level_6_or_7`, which asserts no preset carries level-6 or level-7 and passes today. report-01.md's Findings table names this exact comment as the contradiction it resolved (*"Contradiction resolved"*); the landed diff never touched it.
- **Why it matters:** this is the epic's own doc-contract-divergence archetype, sitting in the file the plan owns, and it is the one site a maintainer reads before editing the payloads. An author who trusts it and adds `level-7` to a preset gets a red test they were told to expect a green one for. It also makes a report claim false — a run report asserting a fix that never landed is exactly the false signal this epic exists to remove.
- **Fix:** rewrite the comment so it states the two facts that are actually true and separates them: (a) `RESERVED_LEVELS` is empty, so the import-time validator rejects nothing beyond `ALLOWED_LEVELS`; (b) as a *policy* — not a validator constraint — no preset uses `level-6`/`level-7` because both resolve to alias-capability-gated efforts (opus xhigh / fable max) that fall back silently when the resolved alias lacks the capability, so those two tiers are explicit per-phase opt-in only, and `test_high_end_reaches_level_5_but_never_level_6_or_7` enforces that. While in the file, fix the companion advice in `_validate_level_keyword` (`:429-432`), whose error message tells the caller to *"use 'level-7' for the current top tier"* — the tier the module now says is opt-in only; point it at `level-5` instead, or drop the recommendation.
- **Done when:** `grep -n "may reference" marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` returns nothing, and no statement in the file implies a preset may carry `level-6`/`level-7`.
- **Module/topic:** `plan-marshall:plan-marshall` — `effort_presets.py` (effort ladder)

## G2 — Add `identify` to the `effort` row of the manage-config SKILL.md API-Reference verb table

- **Kind:** incomplete-sweep
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/SKILL.md:594` — the `| `effort` |` row of the `## API Reference` "Noun / Key Verbs" table
- **What is wrong:** the row enumerates `read`, `resolve-target`, `apply-preset --preset`, and `set --scope … --level`, but not the `identify` verb this plan added. The parallel table in `standards/api-reference.md:388` *was* updated, and the same SKILL.md's `## Canonical invocations` section *was* given an `### effort identify` block at `:1217`. Only this one table was missed. Every other noun's row in the table lists its full verb set (e.g. `finalize-steps` lists all three of its verbs), so the table reads as exhaustive rather than curated.
- **Why it matters:** the SKILL.md API-Reference table is the surface an agent scans to learn which verbs a noun supports before consulting the full standard. An agent that reads it concludes `effort identify` does not exist and falls back to the LLM deep-equality eyeball `effort-menu.md` Step 1 now explicitly forbids — reintroducing the untrustworthy signal this plan replaced.
- **Fix:** append to the `effort` row, matching the row's existing style: `` `identify` (read-only preset recogniser: `current` / `previous-ladder` / `custom` / `not_configured`) ``.
- **Done when:** the `effort` row of `manage-config/SKILL.md` § API Reference names `identify`, and the verb set in that row matches the verbs in `standards/api-reference.md`'s `effort` verb table.
- **Module/topic:** `plan-marshall:manage-config` — SKILL.md / api-reference.md

## G3 — Add `effort identify` to the `_cmd_effort.py` module docstring's "Handles:" list

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_cmd_effort.py:5-13` — the `Handles:` block of the module docstring
- **What is wrong:** the block enumerates the five `effort read` forms plus `resolve-target`, `apply-preset`, and `set`. `identify` was added to this very module by this plan (`cmd_effort_identify` at `:868`) and is not listed. Confirmed: `grep -c identify` over the first 45 lines returns 0.
- **Why it matters:** the docstring is the module's own inventory of its command surface, read first by anyone extending the handler. A missing entry makes the next reader believe the file has four verbs when it has five, and invites a duplicate implementation.
- **Fix:** add a line to the `Handles:` block in the existing column-aligned style: `    effort identify                      (preset recogniser; read-only)`.
- **Done when:** the `Handles:` block in `_cmd_effort.py` lists every verb `manage-config.py` dispatches to a `cmd_effort_*` handler.
- **Module/topic:** `plan-marshall:manage-config` — `_cmd_effort.py`

## G4 — Add `identify` to the `effort_presets.py` row of the effort-menu Cross-References table

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/standards/effort-menu.md:89` — the `effort_presets.py` row of the `## Cross-References` table
- **What is wrong:** the row describes the class as *"`EffortPresets` constant-class — per-preset payloads, `get`, `all_names`, `describe`."* It omits `identify`, which the same document's rewritten Step 1 (`:27-40`) now depends on and names by reference (*"matches the current presets first and then the pre-respread shapes recorded in `EffortPresets._LEGACY_PRESETS`"*).
- **Why it matters:** the document's own cross-reference contradicts its own workflow step about which methods the class exposes — a reader checking the table before Step 1 finds no method that could produce the classification Step 1 requires.
- **Fix:** change the row's method list to `` `get`, `all_names`, `describe`, `identify` ``.
- **Done when:** the `effort_presets.py` cross-reference row in `effort-menu.md` names every `EffortPresets` classmethod the document's workflow relies on.
- **Module/topic:** `plan-marshall:marshall-steward` — `effort-menu.md`

## G5 — Re-point the finalize-steps "mirroring effort-menu Step 1" cross-references

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/marshall-steward/references/wizard-flow.md:372` and `marketplace/bundles/plan-marshall/skills/marshall-steward/references/menu-configuration.md:282` — identical sentences
- **What is wrong:** both read *"Optionally detect the current preset first — deep-equality of `plan.phase-6-finalize.steps` against `FinalizeStepPresets.get(name)` for each name in `FinalizeStepPresets.all_names()` — and surface it as `Current: {name} preset` / `Current: custom (manually edited)`, **mirroring effort-menu Step 1**."* Effort-menu Step 1 no longer does an LLM-side deep-equality walk: `effort-menu.md:27` now says *"do **not** eyeball the deep-equality yourself"* and calls `manage-config effort identify`. The two sentences cite a mechanism that no longer exists at the site they cite.
- **Why it matters:** an agent following the cross-reference to see how the pattern is done finds the opposite instruction, and the appeal to authority ("mirroring effort-menu Step 1") now argues for the practice effort-menu explicitly bans. It also silently records that the finalize-steps picker has the same deep-equality brittleness this plan fixed for effort — with no recogniser and no legacy-shape handling.
- **Fix:** drop the "mirroring effort-menu Step 1" clause from both sentences, or replace it with a note that the effort menu uses the deterministic `manage-config effort identify` recogniser and that `finalize-steps` has no equivalent verb yet. Keep both files identical to each other, as they are today.
- **Done when:** `grep -rn "mirroring effort-menu Step 1" marketplace/` returns nothing, or every remaining occurrence describes effort-menu Step 1 as a deterministic script call rather than an LLM deep-equality walk.
- **Module/topic:** `plan-marshall:marshall-steward` — `wizard-flow.md` / `menu-configuration.md`
