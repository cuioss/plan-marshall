# Gaps — 200-respread-the-effort-preset-ladder

**Source:** verification.md (same directory)   **Open items:** 8

The ladder values, the migration recogniser, and every test guard are correct — verified by executing
the module against the real pre-change payloads and by three independent mutation checks that all
went red. Every gap below is a documentation-surface miss, in three families:

- **G1** — one stale statement that inverts the shipped level-6/7 policy inside the plan's own primary
  file, and which report-01.md claims to have fixed.
- **G2–G5** — four sites where the new `effort identify` verb (or the mechanism change it caused) was
  not carried through.
- **G6–G8** — three sites where the **`balanced` preset's prose omits slots that sit BELOW its stated
  default**, so the narrative reconstructs to a different ladder than the payload ships. Found during
  adversarial review; D3's *Done when* ("the payloads and their descriptions agree") is the condition
  they fail.

## G1 — Delete the "presets may reference level-7" clause from the `RESERVED_LEVELS` comment

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py:86-88` — the comment above `RESERVED_LEVELS`
- **What is wrong:** the comment reads *"No effort levels are currently reserved. `level-7` is the current top tier (resolves to fable, max — sits above Opus) **so presets may reference it**."* After the re-spread, four other sites say the opposite: the module docstring at `:37-42` (*"`level-6`/`level-7` are NOT used as preset defaults … stay reserved for explicit per-phase opt-in"*), `_DESCRIPTIONS['high-end']` at `:295` (*"level-6/level-7 stay opt-in only (alias-gated)"*), `doc/user/efforts.adoc:67` (*"`level-6`/`level-7` are **not** used by any preset"*), and — executably — `test/plan-marshall/plan-marshall/test_effort_presets.py::test_high_end_reaches_level_5_but_never_level_6_or_7`, which asserts no preset carries level-6 or level-7 and passes today. report-01.md's Findings table names this exact comment as the contradiction it resolved (*"Contradiction resolved"*); the landed diff never touched it.
- **Why it matters:** this is the epic's own doc-contract-divergence archetype, sitting in the file the plan owns, and it is the one site a maintainer reads before editing the payloads. An author who trusts it and adds `level-7` to a preset gets a red test they were told to expect a green one for. It also makes a report claim false — a run report asserting a fix that never landed is exactly the false signal this epic exists to remove.
- **Fix:** rewrite the comment so it states the two facts that are actually true and separates them: (a) `RESERVED_LEVELS` is empty, so the import-time validator rejects nothing beyond `ALLOWED_LEVELS`; (b) as a *policy* — not a validator constraint — no preset uses `level-6`/`level-7` because both resolve to alias-capability-gated efforts (opus xhigh / fable max) that fall back silently when the resolved alias lacks the capability, so those two tiers are explicit per-phase opt-in only, and `test_high_end_reaches_level_5_but_never_level_6_or_7` enforces that. While in the file, fix the companion advice in `_validate_level_keyword` (`:429-432`), whose error message tells the caller to *"use 'level-7' for the current top tier"* — the tier the module now says is opt-in only; point it at `level-5` instead, or drop the recommendation. ⛔ **Scope this to `effort_presets.py` only.** `manage-config/scripts/_cmd_effort.py` carries a deliberately-parallel `RESERVED_LEVELS` block (`:60-63`) and an identical *"use `level-7` for the current top tier"* string (`:118-119`), and **neither is a second instance of this defect**: the comment there stops before the "so presets may reference it" clause, and that module validates a **user-supplied per-scope** level (`effort set --level`), where `level-7` opt-in is exactly the sanctioned path. Changing them would introduce the error this gap removes. Verified by reading both blocks during adversarial review.
- **Done when:** `grep -n "may reference" marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` returns nothing, no statement in that file implies a preset may carry `level-6`/`level-7`, and `_cmd_effort.py` is unchanged.
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
- **What is wrong:** the block enumerates the five `effort read` forms plus `resolve-target`, `apply-preset`, and `set`. `identify` was added to this very module by this plan (`cmd_effort_identify` at `:973`) and is not listed. Confirmed: `grep -c identify` over the first 45 lines returns 0.
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

## G6 — `EffortPresets.describe('balanced')` never mentions the three slots that sit below its stated default

- **Kind:** incomplete-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py:282-289` — the `'balanced'` entry of `_DESCRIPTIONS`
- **What is wrong:** the string reads *"default level-4 (opus medium), with the analytical phases at level-4 and the highest-value slots (phase-3-outline, phase-5-execute.default, phase-6-finalize.post-run-review) at level-5 (opus high); summed-level spread 36."* It names every slot that sits **above** the stated default and **no slot that sits below it**. Three of the nine slots do: `phase-5-execute.verification-feedback`, `phase-6-finalize.verification-feedback`, and `phase-6-finalize.default` are all `level-3`. Reconstructing the payload from this sentence alone (default level-4 everywhere except the named level-5 lifts) yields a summed-level spread of **39**; the payload ships **36**. Re-derived by executing the module: `EffortPresets.get('balanced')` returns `phase-6-finalize` = `{'default': 'level-3', 'verification-feedback': 'level-3', 'post-run-review': 'level-5'}` and `phase-5-execute.verification-feedback` = `'level-3'`. `balanced` is the only preset with any slot below its own `default`, and it is the only one of the three whose description omits the remainder — `describe('economic')` and `describe('high-end')` each account for every slot.
- **Why it matters:** this string is not internal commentary. `effort-menu.md:44` and `:56` specify that the wizard's `AskUserQuestion` option description is *"sourced verbatim from `EffortPresets.describe(name)`"*, so this is the text an operator reads at the moment they pick a cost tier. It tells them `balanced` runs the finalize phase at level-4 (Opus medium); `apply-preset balanced` writes level-3 (Sonnet high) there. D3's *Done when* is precisely "the payloads and their descriptions agree", and for `balanced` they do not.
- **Fix:** extend the `'balanced'` description with the below-default remainder, matching the clause style `describe('high-end')` already uses for its own remainder: after *"…at level-5 (opus high)"*, insert `', keeping the triage (verification-feedback) slots and phase-6-finalize.default at level-3'`.
- **Done when:** reconstructing each preset's nine slots from its `_DESCRIPTIONS` string alone (default applied to every slot not explicitly named) reproduces `EffortPresets.get(name)` exactly, for all three names.
- **Module/topic:** `plan-marshall:plan-marshall` — `effort_presets.py` (preset descriptions)

## G7 — the `BALANCED` docstrings omit `phase-6-finalize.default: level-3`

- **Kind:** incomplete-statement
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py:20-28` (the `BALANCED` bullet of the module docstring) and `:161-172` (the `BALANCED` attribute docstring)
- **What is wrong:** both say *"…to `level-5` (opus, high), keeping the triage (verification-feedback) slots at `level-3`."* That accounts for two of the three level-3 slots. `phase-6-finalize.default` is also `level-3` and is named nowhere. Reconstructing from these two docstrings yields a summed-level spread of **37**; the attribute docstring's own next sentence states **36**, so the text contradicts itself. This is a distinct defect from G6 — the `_DESCRIPTIONS` string omits all three level-3 slots, these two docstrings omit exactly one — and the sibling docstrings do it right: `ECONOMIC` closes with *"keeping every other slot at `level-3`"* and `HIGH_END` with *"keeping only the triage (verification-feedback) and finalize-default slots at `level-4`"*.
- **Why it matters:** this is the docstring a maintainer reads before editing the `BALANCED` payload, and the omitted slot is the one that makes `balanced` and `economic` identical at `phase-6-finalize.default` — a non-obvious property of the shipped ladder that a reader would otherwise have to diff the payloads to discover. Demonstrated concretely: setting that one slot to `level-4` (the value the prose implies) moves the spread to 37 and turns `test_get_balanced_returns_balanced_preset`, `test_preset_spread_matches_target[balanced]`, and `test_preset_spread_ladder_is_evenly_distributed` red — so the prose describes a ladder the test suite rejects.
- **Fix:** in both docstrings, replace *"keeping the triage (verification-feedback) slots at `level-3`"* with *"keeping the triage (verification-feedback) slots and `phase-6-finalize.default` at `level-3`"*.
- **Done when:** the `BALANCED` bullet in the module docstring and the `BALANCED` attribute docstring each account for all nine slots, and summing the levels they describe gives 36.
- **Module/topic:** `plan-marshall:plan-marshall` — `effort_presets.py` (preset docstrings)

## G8 — the `balanced` row of the user-guide preset table omits `phase-6-finalize.default: level-3`

- **Kind:** incomplete-statement
- **Severity:** medium
- **Where:** `doc/user/efforts.adoc:66` — the `balanced` row of the "Recommended starting point — presets" table
- **What is wrong:** the row reads *"Default `level-4` (Opus medium). Lifts the analytical phases (`phase-2-refine`, `phase-4-plan`) to `level-4` and the highest-value reasoning slots (…) to `level-5` (Opus high); triage stays at `level-3`. Summed-level spread 36."* As in G7, `phase-6-finalize.default` is `level-3` and is not named, so the row reconstructs to 37 while stating 36. The `high-end` row immediately below (`:67`) proves the table's own convention: it explicitly says *"only the triage (`verification-feedback`) and finalize-default slots stay at `level-4`"*. Only the `balanced` row drops the finalize-default clause.
- **Why it matters:** `doc/user/efforts.adoc` is the page the plan named as D4's sample and the page an operator reads to choose a tier. The row understates the finalize phase by one level on the middle rung — the rung most projects will land on — so a user budgeting from this table budgets Opus where Sonnet runs. It is also an internal inconsistency inside a three-row table, which is the cheapest kind of doc defect to notice and the most corrosive to leave.
- **Fix:** in `doc/user/efforts.adoc:66`, replace `triage stays at `level-3`` with ``the triage (`verification-feedback`) slots and `phase-6-finalize.default` stay at `level-3```, mirroring the `high-end` row's phrasing at `:67`.
- **Done when:** each of the three rows in that table names every slot whose level differs from the row's stated default, and summing the levels each row describes reproduces the spread number that row states (30 / 36 / 41).
- **Module/topic:** `doc/user` — `efforts.adoc`

## Refuted during adversarial review

**No gap was refuted.** G1–G5 were each re-checked against the tree by an independent agent and all
five stand; the corrections applied were to citations and scope, not to the findings. Two candidate
gaps were **considered and deliberately not filed**, recorded here so they are not re-raised:

| Candidate | Why it was NOT filed |
|---|---|
| `manage-config/scripts/_cmd_effort.py:60-63` mirrors `effort_presets.py`'s `RESERVED_LEVELS` comment, and `:118-119` repeats the *"use `level-7` for the current top tier"* advice G1 flags — apparently a second instance of G1 | Read in full: the `_cmd_effort.py` comment stops at *"`level-7` is the current top tier (resolves to fable, max — sits above Opus)"* and **does not** carry the *"so presets may reference it"* clause that makes G1 a contradiction. The `:118-119` string belongs to `validate_effort_level`, which validates a **user-supplied per-scope** level (`effort set --scope … --level`) — the exact opt-in path the module's own policy sanctions for `level-6`/`level-7`. Both statements are correct in context. Recorded as a scope warning inside G1's **Fix** so a fixer does not "harmonise" them into an error |
| `plan-marshall/standards/effort-roles.md:171` says *"`BALANCED` is stored in literal-expanded form"* — singular, while all three presets are literal-expanded and the deep-equality recogniser depends on all three being so | Pre-existing, not a regression of this plan: the same singular phrasing is present at `55639a50^`, and all three presets were literal-expanded before the re-spread too. The row restates no tier value, so it never fell inside D4's declared population. Noted in verification.md § What could NOT be verified as pre-existing residue for a later sweep rather than charged to this plan |
