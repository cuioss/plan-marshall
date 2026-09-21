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

# Config knobs that stay unset are undiscoverable — surface every knob in `marshal.json`

**Epic:** truthful-signals
**Branch prefix:** fix

## Problem

`DEFAULT_ORCHESTRATOR` seeds only `auto_emit`. The `effort` sub-block and the `parallelization_scope`
scalar are deliberately left unset so readers fall through to implicit defaults. The result is a knob
that **exists, validates, and is settable, but never appears in `marshal.json`** — so a user reading
their own config has no way to discover it exists at all.

`parallelization_scope` is fully implemented: validated, present in the settable-scalar set, and
consumed by the orchestrator's `next` verb. Ask for it and you get `value: null, set: false`. `effort`
is likewise a legal, writable key of the same block that never appears in a seeded file.

This is **not a new preference** — it violates an already-established house rule. The
`recipe-marshal-json-config-audit` **Aspect 1 — Default-surfacing completeness** requires verifying
that every code-side default reaches `marshal.json`, and **flagging any that exists in code but is
absent from the file**. That is precisely this gap, and the recipe's prescribed remedy —
"materialises the missing defaults" — is precisely this plan.

⭐ **The violation survived because a comment defends it.** The code states the unset-ness as
deliberate design ("stay unset (implicit defaults) so every orchestrator reader falls through to
today's values"), and repeats it further down. A reader auditing the block finds a rationale and moves
on. **The comment must be CORRECTED, not preserved** — it currently documents a house-rule violation
as intentional design. This is a distinct archetype worth naming: *documentation that makes a gap look
intentional and therefore invisible to review.*

## Goal

`marshal.json` is the discovery surface it is supposed to be: every seeded-able knob appears in it
with its effective default, the comments describe the surfacing rule rather than a rationale for
breaking it, and **no effective behaviour changes** — a materialised default resolves exactly as the
unset key did.

## Deliverables

1. **D1 — GATE: settle what "expose every knob" means mechanically.** Mutates nothing. Decide:
   - **(a)** Does every knob get materialised **with its effective default value**
     (`parallelization_scope: 1`), or with a null/commented placeholder? **Value-materialisation is
     recommended** — a `null` placeholder is as undiscoverable as absence for the *"what can I set?"*
     question, and it re-introduces the fall-through ambiguity.
   - **(b)** How is the `effort` **sub-block** surfaced, given it is a nested shape rather than a
     scalar — the full default sub-block, or its scalar leaves?
   - **(c)** Confirm the **no-behaviour-change invariant** and **name the test that proves it**.
   *Done when:* all three verdicts are recorded, and (c) names a specific test.
   ⛔ **Surfacing a knob must not change its effective default.** Materialising
   `parallelization_scope: 1` must behave identically to leaving it unset. The fall-through values are
   real — `plan.effort` for the baseline effort of the read-only orchestrator surfaces, an unset-`max`
   no-op for the uplift ceiling, and a hard-coded scope of 1 — and must be preserved behaviourally.
2. **D2 — Surface the orchestrator block's knobs.** Extend `DEFAULT_ORCHESTRATOR` per D1 so
   `sync-defaults` materialises `parallelization_scope` and the `effort` sub-block alongside
   `auto_emit`.
   *Done when:* a freshly seeded `marshal.json` carries all three.
   ⛔ **A default-shape change must migrate ALL config surfaces**, per the config-design principles'
   rule on the subject. **Enumerate them explicitly in the success criteria** rather than assuming the
   seeded copy is the only one — an unmigrated surface is how this lands half-done and looks complete.
3. **D3 — Correct the comments that defend the gap.** Rewrite the two commentary sites so they
   describe the surfaced shape and the default-surfacing rule, instead of presenting deliberate
   absence as correct design. Add the cross-reference to Aspect 1 / the config-design principles so
   the next reader meets **the rule**, not a rationale for breaking it.
   *Done when:* neither comment can be read as authorising an unsurfaced knob.
4. **D4 — Sweep for other code-default-but-not-in-file gaps.** The orchestrator block is the instance
   that was hit; **the rule is global**. Run the Aspect-1 trace across every `DEFAULT_*` block: for
   each code-side default, does it reach `marshal.json`? Produce the gap list and materialise it.
   *Done when:* the gap list exists with the population it was derived from, and each gap is either
   closed or recorded with a reason.
   ⛔ **SPLIT GUARD — this deliverable may be deferred rather than done.** If the sweep returns a
   large gap list, **D4 splits into its own plan rather than inflating this one.** Record the count at
   D1 and decide then; do not silently absorb an open-ended sweep.
5. **D5 — Tests.**
   - (a) A seeded `marshal.json` contains every knob D1 says it must — **the assertion that fails
     against today's `DEFAULT_ORCHESTRATOR`**, so it pins the fix rather than the defect.
   - (b) The no-behaviour-change invariant: a materialised default resolves identically to the unset
     key, for `parallelization_scope` **and** for `effort`.
   - (c) Validation still accepts **both** the newly-seeded shape and a legacy file whose block carries
     only `auto_emit`. ⛔ **An existing consumer's file must not become invalid.**
   *Done when:* all three hold, with (c) demonstrated against a legacy-shaped fixture.

Five deliverables, under the split presumption — with D4 carrying its own escape hatch.

## Out of scope

- **Redesigning any knob's semantics or its default value.** The plan makes knobs *visible*; changing
  what they do, or what they default to, is a separate decision with user-visible consequences and no
  operator here to approve them.
- **Documenting keys this plan does not newly materialise.** The config-audit recipe requires every
  surfaced key be documented, but widening to a full documentation audit turns a bounded change into
  an open-ended one. In scope: the keys this plan surfaces. Out: the rest.
- **The key-ordering contract itself.** A sibling plan in this epic owns canonical top-level key
  ordering in the same bundle. This plan **adds keys that ordering must then place** — see Notes for
  the sequencing.

## Expected surface

- `marketplace/bundles/plan-marshall/skills/manage-config/scripts/_config_defaults.py` —
  `DEFAULT_ORCHESTRATOR`, the two commentary sites, and `validate_orchestrator_block`.
- The `sync-defaults` deep-merge path and the `setup` seeding site — **touched only if** D1's chosen
  shape needs merge changes rather than a larger default dict.
- `doc/user/configuration.adoc` — for the keys this plan newly materialises only.
- `test/plan-marshall/manage-config/**`.
- **D4 only:** every other `DEFAULT_*` block in `_config_defaults.py`. The D1 count decides whether D4
  stays here or splits.

## Claim labels

⚠⚠ **This plan is derived from a spec that carried NO claim-label section.** Labels were deliberately
**not** retrofitted at authoring time: assigning `OBSERVED` to a claim the author did not personally
verify manufactures provenance, and a wrong label reads as a checked one — which is worse than a
missing one.

⇒ **Treat EVERY claim below as `HYPOTHESIS` until this run verifies it**, including every count, every
file path, and every asserted absence. ⭐ **Asserted absences are the higher-risk half.** **Labelling
is this run's job, before any deliverable is sized.**

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| `DEFAULT_ORCHESTRATOR` is exactly `{'auto_emit': False}` | HYPOTHESIS | `_config_defaults.py` § `DEFAULT_ORCHESTRATOR` — **by symbol**, not by line |
| `parallelization_scope` is validated, settable, and consumed, yet returns `set: false` | HYPOTHESIS | run `manage-config orchestrator get --field parallelization_scope`; then read the validator and the settable-scalar set |
| `effort` is a legal writable key of the block that never appears in a seeded file | HYPOTHESIS | the validator's `known_keys`, and the effort-writing path. An asserted **absence** on the seeding side |
| Two code comments present the unset-ness as deliberate design | HYPOTHESIS | `_config_defaults.py` — locate the commentary **by content**; the reported line numbers are leads |
| Aspect 1 of the config-audit recipe requires materialising code-side defaults into the file | HYPOTHESIS | that recipe's own text — ⛔ **read it before relying on it**; this plan's whole justification rests on it |
| The fall-through values are `plan.effort`, an unset-`max` no-op, and a hard-coded scope of 1 | HYPOTHESIS | the orchestrator readers that consume them. ⛔ **These must be preserved behaviourally**, so verify each before materialising anything |
| A consumer at an older version carries exactly `{"auto_emit": false}` | HYPOTHESIS | operator-reported from another machine — **not reachable from this clone**. Treat as motivation, not evidence; D5(c) covers the compatibility requirement it implies |
| There are further code-default-but-not-in-file gaps beyond the orchestrator block | HYPOTHESIS | **D4's own sweep** — the gap list is unknown at authoring time and its size decides whether D4 splits |
| No existing mechanism already materialises these defaults | HYPOTHESIS | ⛔ asserted **absence**, the higher-risk half — check the seeding and merge paths before extending the default dict |

An asserted **absence** is verified exactly as an asserted presence, and is the higher-risk half.
Every count above is a **lead** — re-derive it at the moment of the claim.

## Verification

- ⛔ **D3's rewritten comments are text-whose-value-is-what-a-reader-does**, so they get a **cold
  read**: give the Step 6 verification sub-agent only the new comment text plus a hypothetical new
  knob, and ask whether that knob should be seeded into `marshal.json`. The correct answer is **yes**.
  If the reader concludes it may legitimately stay unset, the rewrite has reproduced the defect it was
  meant to remove.
- **D5(b) is the load-bearing test.** Behavioural equivalence between a materialised default and an
  unset key is what makes this change safe; without it the plan is a behaviour change wearing a
  discoverability label.
- **D5(c) must run against a genuinely legacy-shaped fixture**, not a synthesised one that happens to
  omit the keys — the compatibility claim is about files that already exist on users' machines.
- D4 must **publish the population it scanned** alongside the gap count. A gap list with no
  denominator is a sample, not a sweep.
- Python, test, and doc changes are expected, so the build gate takes its full path.

## Notes

- ⚠ **Sequencing — run AFTER the key-order canonicalization plan in this epic.** That plan settles the
  canonical top-level ordering; this one **adds keys that ordering must then place**. Running this
  first means the other re-canonicalizes a shape that just changed, and the two fight over canonical
  order. Different files in the same bundle: **serialize, do not parallelize.**
- **A self-correction worth preserving.** On first analysis the orchestrator reported the consumer's
  `auto_emit`-only config as "correct and complete, not short", reasoning from the defending code
  comment — and was **wrong**. It took the comment as authority without checking it against the
  project's own config-governance rule. That is this epic's archetype turned inward: a confident local
  statement trusted over ground truth. Do not repeat it here — read the rule, not the comment.
- ⛔ **Do not go looking for the orchestrator spec or any landing record.** They live under `.plan/`,
  which is git-ignored and absent from this clone. Everything needed is in this file.
