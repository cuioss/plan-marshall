> ⛔ **FIRST INSTRUCTION — do not skip, do not delete, do not move below the title.**
>
> Before reading the rest of this plan and before any other action, load the working contract that
> governs this run:
>
> ```text
> Skill: cloud-plan-lane
> ```
>
> It owns the branch/PR/review-comment cycle, the build gate, the pre-PR verification sub-agent, the
> run report, and the closing self-check. **Nothing in this plan overrides it** — where this plan and
> the contract disagree, the contract wins, and the disagreement is reported.
>
> If the skill cannot be loaded, **stop and report the run blocked**. Do not reconstruct the workflow
> from this file: the parts that matter most — the merge gate, the verification dispatch, the report
> — are not in here.
>
> This block is part of the plan, not part of the template. It survives into every copy.

# Re-spread the effort preset ladder so its three rungs are genuinely distinct

**Epic:** truthful-signals
**Branch prefix:** feature

## Problem

The three effort presets do not form an even ladder. Measured over the nine slots each preset defines,
summing the level number as a crude spread metric:

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

⭐ **The ladder is front-loaded**: `economic → balanced` is **+7**, `balanced → high-end` only **+4** —
the cheap step is nearly twice the expensive one.

⭐⭐ **The sharper form of the same fact:** `high-end` is **identical to `balanced` in five of nine
slots** (bolded), differs in only four, and **never exceeds level 4 anywhere**. Choosing `high-end`
buys almost nothing over the default.

The requested fix: move `economic` up to today's `balanced` values, make `high-end` genuinely
high-end, and find a new middle.

## ⛔ THE BLOCKER — "really high-end" is unreachable without overturning a documented reservation

The preset module states that **no slot uses level 5**, which is *"reserved for explicit per-phase
opt-in as a cost/intensity policy choice, never a preset default."*

⛔ **Under that reservation `high-end` is nearly saturated.** Only two of its nine slots sit below
level 4. **The maximum possible bump without level 5 is +2, reaching 36** — which would not make it
"really high-end", and would *shrink* the gap by pushing the ceiling down onto the middle rung rather
than raising the top.

⇒ **This is a genuine fork with cost consequences, and this run cannot decide it.**

## Goal

The three presets are measurably distinct along a stated spread target, existing configurations are not
silently reclassified, and every document and consumer that restates the tiers agrees with the values
that shipped.

## Deliverables

1. **D1 — GATE: settle what can be settled, and RECORD PROPOSALS for what cannot.** Mutates nothing.
   Four questions:
   - ⛔ **May `high-end` use level 5?** The request implies yes; the code explicitly forbids it.
     **⛔ THIS RUN MUST NOT DECIDE IT.** It is a cost/intensity policy choice, and there is no operator
     present. **Record both options with their consequences as a proposal**, and proceed under the
     no-level-5 reading for anything downstream.
     ⚠ **If the answer is ever yes, the reservation comment and every document restating it must change
     in the same change** — a value change that leaves prose forbidding it is this epic's
     doc-contract-divergence archetype.
   - **Which "default" is meant?** Two readings: the `default:` key **inside** each preset payload, or
     **which preset ships as the default** for a new project. ⚠ **Unrelated changes with different blast
     radii.** If the request cannot be disambiguated from the text, **record the ambiguity as a proposal
     rather than picking one.**
   - **Name the new middle preset and state the target spread as a NUMBER.** Old `balanced` becomes
     `economic`, so the middle rung is vacant. ⚠ **Reusing the name `balanced` for a different value set
     is the most confusing option available** — see the migration hazard in D2.
   - ⚠ **Acknowledge that the cheapest tier gets more expensive.** Old `balanced` (30) replacing old
     `economic` (23) is a **~30% floor increase for every project on `economic`** — the preset a
     cost-sensitive user deliberately chose. **This is a real consequence of the request and belongs in
     the report explicitly, not discovered in a bill.**
   *Done when:* each question is either settled with its reasoning, or recorded as a proposal for the
   operator with its options and consequences.
   ⛔ **STOP CONDITION.** If the level-5 question is load-bearing for the requested outcome — and it
   appears to be, since +2 is all that is otherwise available — **the run ships D2 and stops before D3,
   reporting the fork.** Shipping a re-spread that does not achieve the stated goal, without saying so,
   would be the epic's own archetype.
2. **D2 — MIGRATION: the wizard matches presets by DEEP EQUALITY.** The preset payloads mirror the
   on-disk shape produced by applying a preset, **so the configuration wizard recognises a project's
   preset by deep-equality match.**
   ⛔ **Consequence, and the highest-risk part of this plan:** every existing configuration holding the
   *old* `economic` shape **stops matching any preset the moment the payloads change**. The wizard would
   report those projects as **custom / unrecognised** — a silent reclassification of working
   configurations, with no error and no migration path.
   *Done when:* legacy shapes are recognised and offered a re-apply, or old→new is mapped explicitly.
   ⛔ **Do not ship the value change without this.**
   ⚠ This is the same deep-equality brittleness the defaults-sync already handles for retired step ids —
   **there is an in-tree precedent for the shape of the fix; find it before inventing one.**
   ⭐ **D2 is independently valuable and ships even if D1 halts D3** — the brittleness exists today.
3. **D3 — Apply the new ladder.** Edit the three payloads **and the description strings**, which restate
   the tiers in prose and will otherwise contradict the values.
   *Done when:* the payloads and their descriptions agree.
4. **D4 — Update the FULL documentation population, not the named sample.**
   ⚠ **The request named one user page — that is a SAMPLE, not the population.** A single-token search
   returns roughly seven sites, **two of which are code**: the preset definitions themselves, and a
   retrospective routing-verification script that **reasons about preset identity**.
   ⛔ **That consumer script is the non-obvious one:** if the retrospective reasons about preset names or
   values, a re-spread can change **retrospective verdicts on past runs**. **Verify what it does before
   assuming a documentation-only edit suffices.**
   *Done when:* every site is updated, and the population was derived by sweeping **all three preset
   names plus the apply verb** — not one token.
   ⚠ **Re-derive the list**: the seven-site figure came from a single-token search and misses any site
   naming only `balanced` or `high-end`.
5. **D5 — Tests.** Payload round-trip (apply → on-disk shape → wizard recognises it) for **all three**
   presets; the D2 legacy-shape migration; and a **spread assertion** encoding D1's chosen distribution.
   *Done when:* all pass, each seen red first.
   ⭐ **The spread assertion is what stops this plan being needed a third time** — without it the ladder
   can silently drift back to front-loaded.

Five deliverables, under the split presumption.

## Out of scope

- ⛔ **Deciding the level-5 policy.** See D1. It is a cost decision with no operator present, and the
  lane forbids self-approving that class of change.
- **Changing which preset a new project gets by default**, unless D1 establishes that is what was meant.
  Picking the more expensive reading of an ambiguous request, unprompted, is not a judgement call this
  run should make.
- **Redesigning the effort-role slot set.** The plan re-spreads values across the existing nine slots;
  adding or removing slots is a different change with a much wider surface.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/effort_presets.py` — the three
  payloads, the description strings, and the level-5 reservation comment.
- `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/check-routing-decisions.py` —
  ⚠ **a code consumer that reasons about presets.**
- `marketplace/bundles/plan-marshall/skills/plan-marshall/standards/effort-roles.md`,
  `manage-config/standards/api-reference.md`,
  `marshall-steward/standards/effort-menu.md` (the wizard's match step),
  `plan-retrospective/references/routing-decision-verification.md`.
- `doc/user/efforts.adoc` — the named sample.
- The per-phase seeded defaults in `manage-config/scripts/_config_defaults.py` whose comments describe a
  *"balanced-preset baseline"* — ⛔ **confirm whether the defaults are seeded FROM the preset or from a
  literal copy**; if a copy, they drift the moment the payload changes.
- `doc/concepts/execution-context.adoc`.
- Tests.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including the whole table
above. ⭐ **Asserted absences are the higher-risk half.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| The nine-slot values are as tabulated, totalling 23 / 30 / 34 | HYPOTHESIS | `effort_presets.py` — **re-derive the whole table**; every number in it is a lead |
| `high-end` matches `balanced` in five of nine slots and never exceeds level 4 | HYPOTHESIS | the same payloads. ⛔ **This is the operator's actual complaint** — confirm it before acting, because if it is wrong the plan has no premise |
| The module reserves level 5 against preset use | HYPOTHESIS | that file's reservation comment — **by content**. ⛔ **This is the blocker; read it verbatim** |
| Only two `high-end` slots sit below level 4, so +2 is the maximum bump | HYPOTHESIS | arithmetic over the confirmed table |
| The wizard recognises a preset by deep-equality match against the payload | HYPOTHESIS | the steward's effort-menu standard and the matching implementation. ⛔ **D2's entire premise** |
| A retired-key migration precedent exists in the defaults-sync path | HYPOTHESIS | that path — ⛔ an asserted **presence**; if it does not exist, D2 grows and must be re-sized |
| The population is seven sites | HYPOTHESIS | ⛔ **produced by a single-token search and explicitly a SAMPLE.** Re-derive across all three names plus the apply verb |
| The retrospective routing-verification script reasons about preset identity | HYPOTHESIS | that script — ⛔ **the highest-consequence unknown**: it could change verdicts on past runs |
| The per-phase seeded defaults are literal copies rather than derived from the preset | HYPOTHESIS | the defaults module and the sync path |
| No other consumer depends on the exact payload values | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — **derive the consumer set; a list produced by looking is a sample** |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim. ⭐ **The spread metric
(summed level numbers) is deliberately crude**: it is adequate to *demonstrate* front-loading, **not to
define the fix**. D1 owns the real target.

## Verification

- ⛔ **D2 must be demonstrated against a genuinely old-shaped configuration**, not a synthesised one that
  happens to differ. The claim is about files that already exist on users' machines, and a synthetic
  fixture cannot test that.
- ⛔ **D5's spread assertion must fail against the current ladder.** If it passes before the change, it
  is not encoding a target — it is decorating one.
- **D4's consumer-script verdict belongs in the report explicitly**: either "the retrospective does not
  depend on preset values" with the evidence, or a statement of what changed for past runs. Silence here
  is the failure mode.
- **Report the derived population and the count of sites changed separately.** A count of files touched
  is a volume, not coverage.
- Python, standards, documentation, and test changes are expected, so the build gate takes its full
  path.

## Notes

- ⚠ **Sequencing:** this shares `doc/user/efforts.adoc` with the configuration-doc split plan in this
  epic. **Prefer that plan first** — splitting into a settled page beats splitting a page whose content
  is mid-rewrite. It also touches config standards adjacent to two other plans here; verify before
  pairing.
- ⛔ **Do not go looking for the orchestrator spec or any landing record.** They live under `.plan/`,
  which is git-ignored and absent from this clone. Everything needed is in this file.
