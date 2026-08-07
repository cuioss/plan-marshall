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

# Self-review has no detector for a duplicate-claimable key, or for a discard path with no report path

**Epic:** code-intelligence-substrate
**Orchestrator plan:** PLAN-CIS-021
**Branch prefix:** feature

## Problem

`ext-self-review-plan-marshall` surfaces deterministic candidate pairs — regexes, symmetric-pair
functions, flag-guard pairs, producer-consumer pairs, source-of-truth duplicates. It has **no
detector** for the two shapes that produced the highest-severity defects on PR #1067, and both are
mechanically detectable: a new keyed collection whose key can be claimed twice, and a discard branch
inside a function that owns a report channel.

The sting is that the plan which shipped #1067 stated the invariant and then broke it one layer up.
Its own contract doc says a resolver whose identity key is claimed by two distinct modules must not
resolve the collision by insertion order — it emits no edge and reports it. Then:

- `discover_derivation_resolvers()` appended resolver ids behind a bare falsiness check, so a truthy
  non-string id such as `1` is admitted, and **two distinct resolvers returning the same string id
  collapse into one producer identity** — the identical archetype, at the resolver-identity layer,
  in the code written to eliminate it at the module-coordinate layer.
- `merge_resolver_edges()` drops self-edges and unknown endpoints **without adding `notes[]`**, so it
  reports `status: ok`, zero edges, and no suppression reason — a vacuous confident zero, inside the
  plan whose stated purpose is anti-vacuity.

⛔ **And `pre-submission-self-review` ran twice at that HEAD, examined 117 candidates, and reported
`self-review clean: no check matched`.** That is the finding: 117 is a *volume*, and none of the 117
candidate classes could express either shape.

## Goal

Both shapes are expressible as deterministic candidate classes, each pinned by a test that fails
against the real pre-fix code, and each narrow enough that its output is read rather than dismissed.

## Deliverables

1. **D1 — candidate class: duplicate-claimable key.** A new dict/set keyed on a caller-supplied
   identity requires an explicit duplicate-key disposition at the insertion site. Detect a
   `dict[k] = v`, or an `.append` onto an identity-bearing collection, inside a loop with no prior
   membership test. Raise at the **insertion site**, not the type declaration.
   *Done when:* the class exists in the registry and fires on the D4(a) fixture.

2. **D2 — candidate class: discard path with no report path.** A discard/skip/`continue` branch
   inside a function that owns a report channel must write to that channel. This is the mechanical
   form of an anti-vacuity rule the project already states in prose.
   *Done when:* the class exists and fires on the D4(b) fixture.

3. **D3 — GATE: derive the population both classes fire on across the current tree.**
   ⚠ Report the hit count **separately** from the number of files examined. Volume-read-as-coverage
   is a recorded recurring archetype here, and "117 candidates examined" is exactly its shape.
   *Done when:* both numbers are published with the command that produced them. **A class firing on
   hundreds of sites is mis-specified and must be narrowed before shipping, not after.**

4. **D4 — tests, each verified to FAIL pre-fix.** (a) the `discover_derivation_resolvers()` shape at
   its pre-fix revision is flagged by D1; (b) the `merge_resolver_edges()` shape at its pre-fix
   revision is flagged by D2.
   ⭐ Both pre-fix revisions exist in git history on the #1067 branch — **use them as fixtures rather
   than synthesizing analogues**, so the tests pin the real defects.
   *Done when:* each test is observed failing before the detector exists and passing after. Prove the
   failing direction; a detector never seen to fire is not known to work.

5. **D5 — documentation.** Add both classes to the `ext-self-review-plan-marshall` candidate-class
   table with their detection shape and their false-positive posture.
   *Done when:* both rows exist and state the posture, not only the shape.

## Out of scope

Making the self-review lens read the plan's own contract doc for its stated invariants and check the
diff against them. That is a semantic/LLM-judgement capability, not a deterministic candidate class,
and folding it in would change this plan from "two mechanical detectors" into "an invariant-extraction
engine." If it is wanted it is its own plan. Recorded so a later reader does not re-derive the
omission as an oversight.

## Expected surface

- `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**` — the
  candidate-class registry and the two detectors — **HYPOTHESIS**
- `test/pm-plugin-development/**` — fixtures and tests — OBSERVED
- the `ext-self-review-plan-marshall` SKILL.md candidate-class table — OBSERVED

## Claim labels

| Claim | Label | Confirm/refute artifact |
|---|---|---|
| Findings `8da924` and `3e04a8` on PR #1067, both Major, both resolution `fixed` | OBSERVED | that plan's `artifacts/findings/pr-comment.jsonl` |
| `pre-submission-self-review` reported `clean: 117 candidates examined, no check matched` | OBSERVED | that plan's `status.json` `phase_steps[6-finalize]`, and `logs/decision.log` |
| **The candidate classes live in one registry a new class can be added to without touching the dispatch path** | **HYPOTHESIS** | the skill's candidate-class registry symbol under `ext-self-review-plan-marshall/` |
| D1's shape is narrow enough not to fire on ordinary accumulator code | **HYPOTHESIS** | settled by D3's population derivation |

⛔ **The registry hypothesis is load-bearing** — if each class is hand-wired instead, the cost of D1
and D2 changes materially. Settle it against the **implementing source** before scoping them; the
SKILL.md description of the candidate classes restates the intent and does not establish the
extension shape.

⛔ **The second hypothesis is this plan's main risk.** A detector that fires everywhere is worse than
no detector, because it trains its readers to dismiss it. If D3 shows a large population, narrow the
shape and re-derive — do not ship it and plan to tune later.

## Verification

- D4 is the durable proof: each detector observed failing against the real pre-fix revision, then
  passing. Synthesized analogues do not count.
- D3's two numbers must be reported separately. A single number that conflates hits with files
  examined reproduces the exact archetype this plan exists to detect.
- **Cloud-specific risk:** D4 depends on reaching historical revisions from the #1067 branch. If this
  clone cannot reach them (shallow clone, pruned branch), say so and report the run blocked on D4
  rather than substituting synthesized fixtures — the plan's value is that the tests pin real code.

## Notes

- Disjoint from the `plan-retrospective` and `manage-architecture` clusters; this is
  `pm-plugin-development`.
- Adjacent to PLAN-CIS-006, which edits a different skill in the same bundle
  (`tools-marketplace-inventory`) — re-verify file sets before pairing.
- Adjacent to PLAN-CIS-015, the companion generalisation: that plan owns the enumeration half, this
  one owns the invariant half. Neither touches the other's files.
- The generalisation worth carrying: **a stated invariant is not a checked invariant** — the third
  distinct confirmation in this project that stating an archetype in prose, even in the document
  being written, does not prevent its recurrence.
