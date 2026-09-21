# PLAN-TRUTH-024: Re-spread the effort preset ladder — economic takes balanced's values, high-end becomes genuinely high-end, and a new middle is found

epic: truthful-signals
workstream: WS-01

> Staged 2026-07-30 from an operator request. **LOW PRIORITY.** *"The effort presets we introduced do not
> fit anymore. They are not distributed evenly. Replace the current economic with the balanced values,
> bump up High-End (that it is really High-End) and find a new balance in between. Update the default and
> ALL documentation like `doc/user/efforts.adoc`."*

## Objective

Re-spread the three effort presets so the ladder has three genuinely distinct rungs. Measured from
`effort_presets.py` (nine slots per preset), `economic` and `balanced` differ materially while
`balanced` and `high-end` collide on four of nine slots — so choosing `high-end` buys almost nothing
over the default. Move `economic` up to today's `balanced` values, make `high-end` genuinely
high-end, and find a new middle. **LOW PRIORITY**, and see the blocker section below: "really
high-end" is unreachable without overturning a documented reservation, so the blocker is settled
first or the plan re-scopes to the two lower rungs only.
## ✅ The uneven-distribution claim is CORRECT and measurable

Derived from `plan-marshall/scripts/effort_presets.py:103-184` (nine slots per preset, level number
summed as a crude but adequate spread metric):

| Slot | `economic` | `balanced` | `high-end` |
|---|---|---|---|
| `default` | 2 | 3 | **3** |
| `phase-2-refine` | 3 | 3 | 4 |
| `phase-3-outline` | 3 | 4 | **4** |
| `phase-4-plan` | 3 | 3 | 4 |
| `phase-5-execute.default` | 2 | 4 | **4** |
| `phase-5-execute.verification-feedback` | 3 | 3 | 4 |
| `phase-6-finalize.default` | 2 | 3 | **3** |
| `phase-6-finalize.verification-feedback` | 3 | 3 | 4 |
| `phase-6-finalize.post-run-review` | 2 | 4 | **4** |
| **Total** | **23** | **30** | **34** |

⭐ **The ladder is front-loaded**: `economic → balanced` is **+7**, `balanced → high-end` is only **+4** —
the cheap step is nearly twice the expensive one.

⭐⭐ **And the sharper form of the same fact: `high-end` is identical to `balanced` in FIVE of nine slots**
(bolded above). It differs in only four, and **never exceeds `level-4` anywhere.** That is the operator's
complaint precisely: *high-end is barely distinguishable from balanced.*

## ⛔ THE BLOCKER — "really high-end" is unreachable without overturning a documented reservation

`effort_presets.py:178-180` states: *"No slot uses `level-5` — `level-5` (opus, high) is **reserved for
explicit per-phase opt-in as a cost/intensity policy choice, never a preset default**."*

⛔ **Under that reservation `high-end` is nearly saturated.** Only two of its nine slots sit below
`level-4` (`default` and `phase-6-finalize.default`, both `level-3`). **So the maximum possible "bump"
without `level-5` is +2 total, reaching 34 → 36** — which would not make it *"really High-End"*, and would
*shrink* the gap problem rather than fix it by pushing the ceiling down onto balanced.

⇒ **D1 must resolve this as a fork, not assume it.** It is a policy decision with cost consequences and
the orchestrator must not make it silently.

## Deliverables

### D1 — GATE: settle four decisions (mutates nothing)

1. ⛔ **Does `high-end` may now use `level-5`?** The request implies yes; the code explicitly forbids it.
   **If yes, the reservation comment and every doc restating it must change in the same plan** — a value
   change that leaves the prose forbidding it is this epic's doc-contract-divergence archetype. **If no,
   state what "really high-end" means within a `level-4` ceiling**, given only +2 is available.
2. **Which "default" does the operator mean?** The request says *"update the default"* and there are two
   readings: (a) the `default:` key **inside** each preset payload, or (b) **which preset is the shipped
   default** for a new project. ⚠ These are unrelated changes with different blast radii. Settle before
   editing.
3. **Name the new middle preset and the target spread.** Old `balanced` becomes `economic`, so the middle
   slot is vacant. Decide the name (reusing `balanced` for a *different* value set is the most confusing
   option available — see the migration hazard below) and the target totals, so "evenly distributed" has a
   number rather than a feeling.
4. ⚠ **Confirm the cheapest tier is allowed to get more expensive.** Old `balanced` (30) replacing old
   `economic` (23) is a **+30% floor increase for every project on `economic`**, which is the preset a
   cost-sensitive user deliberately chose. **That is a real consequence of the request and it should be
   acknowledged explicitly, not discovered in a bill.**

### D2 — ⛔ MIGRATION: the wizard matches presets by DEEP EQUALITY, so changing payloads silently reclassifies existing configs

`effort_presets.py` docstrings state the payloads mirror *"the on-disk shape produced by `apply-preset`
… so the wizard's deep-equality match in `effort-menu.md` Step 1 recognises `Current: economic preset`."*

⛔ **Consequence, and it is the highest-risk part of this plan:** every existing `marshal.json` holding
the *old* `economic` shape **stops matching any preset the moment the payloads change**. The wizard will
report those projects as **custom / unrecognised**, not as "economic" — a silent reclassification of
working configs, with no error and no migration path.

⇒ Decide and implement the migration: recognise the legacy shapes and offer a re-apply, or map old→new
explicitly. **Do not ship the value change without it.** ⚠ Note this is the *same* deep-equality
brittleness class as the retired-key migration `sync-defaults` already handles for step ids — **there is
an in-tree precedent for the shape of the fix.**

### D3 — apply the new ladder

Edit `effort_presets.py`'s three payloads (and the `_DESCRIPTIONS` strings, which restate the tiers in
prose and will otherwise contradict the values).

### D4 — update the FULL documentation population, not the named sample

⚠ **The operator named `doc/user/efforts.adoc` as an example — it is a SAMPLE, not the population.** A
`grep -rln economic` over `marketplace/bundles/` and `doc/` returns **seven** sites, and **two of them are
code**:

| Site | Kind |
|---|---|
| `plan-marshall/scripts/effort_presets.py` | **code** — the definitions (D3) |
| `plan-retrospective/scripts/check-routing-decisions.py` | ⚠ **code** — a *consumer* that reasons about presets |
| `plan-marshall/standards/effort-roles.md` | standard |
| `manage-config/standards/api-reference.md` | standard |
| `marshall-steward/standards/effort-menu.md` | standard — the wizard's match step |
| `plan-retrospective/references/routing-decision-verification.md` | reference |
| `doc/user/efforts.adoc` | **the named sample** (195 lines) |

⛔ **`check-routing-decisions.py` is the non-obvious one:** the retrospective's routing verification
reasons about preset identity, so a re-spread can change *retrospective verdicts on past runs*. **Verify
what it does with preset names/values before assuming a doc-only edit suffices.**

⚠ **Re-derive this list at outline** — it was produced by a single grep on one token (`economic`), so it
misses any site that names only `balanced` or `high-end`. **Sweep all three names plus `apply-preset`.**

### D5 — tests

Preset payload round-trip (`apply-preset X` → on-disk shape → wizard recognises X) for **all three**
presets; the D2 legacy-shape migration; and a **spread assertion** — encode D1's chosen distribution as a
test so the ladder cannot silently drift back to front-loaded. ⭐ **That assertion is what stops this
plan from being needed a third time.**

## Expected surface

- OBSERVED: `plan-marshall/scripts/effort_presets.py:103-184` — the three payloads, values as tabulated
- OBSERVED: `effort_presets.py:178-180` — the `level-5` reservation
- OBSERVED: the seven-site population above (single-token grep; widen at outline)
- HYPOTHESIS: `_config_defaults.py:503,584,600,612,840,1053` — per-phase seeded defaults whose comments
  say *"balanced-preset baseline"*; **if the balanced payload changes, these seeds and their comments may
  drift.** *Confirm/refute:* whether `sync-defaults` seeds from the preset or from a literal copy.
- HYPOTHESIS: `doc/concepts/execution-context.adoc` (cross-referenced from `configuration.adoc:52`)

**Disjointness:** `plan-marshall` (effort_presets) + `plan-retrospective` + `marshall-steward` +
`manage-config` standards + `doc/**`. ⚠ **Overlaps PLAN-TRUTH-023** at `doc/user/efforts.adoc` — 023
splits `configuration.adoc` *into* topic pages including the effort pointer, this one edits
`efforts.adoc`'s content. **Sequence, do not pair.** ⚠ Also touches `manage-config` standards, adjacent to
TRUTH-007 / TRUTH-009.

## Dependencies and Sequencing

- Not blocked. ⚠ **Sequence against PLAN-TRUTH-023** (shared `doc/user/efforts.adoc`) and prefer
  **023 first** — splitting into a settled page beats splitting a page whose content is mid-rewrite.

## Notes

- Low priority by operator instruction.
- ⭐ The spread metric above (summed level numbers) is **deliberately crude** and should not be treated as
  the design target — it is adequate to *demonstrate* the front-loading, not to *define* the fix. D1 owns
  the real target.

## Write-Boundary

Repository source, standards, docs and tests; NO `.plan/local/orchestrator/` writes. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.


---

## ⚠⚠ NO CLAIM LABELS — EVERY CLAIM IN THIS SPEC IS UNLABELLED (recorded 2026-08-09, full-corpus review)

This spec predates the verify-first contract and carries **no `## Claim Labels` section**. The contract
requires every serialized premise to be marked `OBSERVED` or `HYPOTHESIS`, with a `HYPOTHESIS` naming
the file **plus the symbol** that settles it.

⛔ **Labels were NOT retrofitted here, deliberately.** Assigning `OBSERVED` to a claim this orchestrator
did not observe would manufacture provenance — the precise defect the contract exists to prevent, and
worse than the missing section, because a wrong label reads as a checked one.

⇒ **Until outline labels them, treat EVERY claim in this spec as `HYPOTHESIS`**, including its counts,
its file lists, and any asserted *absence*. ⭐ **Asserted absences are the higher-risk half**: an
unverified "X does not exist, build it" produces duplicate work against a surface that already exists,
and nothing downstream trips over it. **Outline owns the labelling before any deliverable is sized.**
