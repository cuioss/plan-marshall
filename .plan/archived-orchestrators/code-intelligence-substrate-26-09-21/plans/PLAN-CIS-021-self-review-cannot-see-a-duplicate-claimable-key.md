# PLAN-CIS-021: Self-review has no detector for a duplicate-claimable key or a discard path with no report path

epic: code-intelligence-substrate
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-30 from the PLAN-02 landing (#1067), inbox message `resolver-ext-point-seam-010`.

## Objective

`ext-self-review-plan-marshall` surfaces deterministic candidate pairs — regexes, symmetric-pair
functions, flag-guard pairs, producer-consumer pairs, source-of-truth duplicates. It has **no detector**
for the two shapes that produced the highest-severity defects on PR #1067, both mechanically detectable:
a new keyed collection whose key can be claimed twice, and a discard branch inside a function that owns
a report channel. Add both candidate classes.

## Why this is ours

Routing test 2: **detector population and derivation** is explicitly in our charter. No PR or review
surface — the *defects* were found by CodeRabbit, but the subject is the local detector's blind spot,
not the review bot's behaviour. (The review-participation half of the same landing went to
`review-apparatus` separately.)

## ⛔ The sting: prose stated the invariant, and the invariant was violated in the code enforcing it

The plan that shipped #1067 **learned this lesson explicitly and then broke it one layer up.**

At `3-outline`, the Q-Gate raised an `under_coverage` finding identifying that the Maven fixture tree
contains two modules declaring the same `com.example:auth-service` coordinate, and that the join keys a
plain dict on `groupId:artifactId` with **last-write-wins**, so one module is silently dropped. The plan
absorbed it thoroughly, and the shipped contract doc states the obligation generically:

> a resolver whose identity key is claimed by two distinct modules MUST NOT resolve the collision by
> insertion order — it emits no edge for that key and reports it.

CodeRabbit then found (finding `8da924`, **Major**) that `discover_derivation_resolvers()` appended
resolver ids behind a bare falsiness check: a truthy non-string id such as `1` is admitted and can abort
every graph query on a mixed `str`/`int` sort, and **two distinct resolvers returning the same string id
collapse into one producer identity.** The identical archetype — two claimants, one key, silent
last-write-wins — recurred **at the resolver-identity layer, in the code written to eliminate it at the
module-coordinate layer, in a document that states the general rule three sections earlier.**

A second (finding `3e04a8`, **Major**): `merge_resolver_edges()` drops self-edges and unknown endpoints
**without adding `notes[]`**, so the resolver can report `status: ok`, zero edges, and no suppression
reason — **a vacuous confident zero, inside the plan whose entire stated purpose is anti-vacuity**, and
whose own contract doc mandates `notes[]` as the required channel for any edge-suppressing condition.

⛔ **`pre-submission-self-review` ran twice at that HEAD, examined 117 candidates, and reported
`self-review clean: no check matched`.** That is the whole finding: 117 is a volume, and none of the 117
candidate classes could express either shape.

## Deliverables

1. **D1 — candidate class: a new dict/set keyed on a caller-supplied identity requires an explicit
   duplicate-key disposition at the insertion site.** Mechanically detectable: a `dict[k] = v` or an
   `.append` onto an identity-bearing collection inside a loop, with no prior membership test. The
   finding is raised at the insertion site, not at the type declaration.
2. **D2 — candidate class: a discard/skip/`continue` branch inside a function that owns a report
   channel must write to that channel.** This is the mechanical form of the anti-vacuity rule the
   project already states in prose, and it would have caught `merge_resolver_edges()` directly.
3. **D3 — GATE: derive the population both classes would fire on across the current tree.** ⚠ Report
   the hit count **separately** from the number of files examined — volume-read-as-coverage is a
   recorded recurring archetype here and `117 candidates examined` is exactly its shape. A class that
   fires on hundreds of sites is mis-specified and must be narrowed before shipping, not after.
4. **D4 — tests, each verified to FAIL pre-fix.** (a) The `discover_derivation_resolvers()` shape at its
   pre-fix revision is flagged by D1. (b) The `merge_resolver_edges()` shape at its pre-fix revision is
   flagged by D2. ⭐ **Both pre-fix revisions exist in git history on the #1067 branch** — use them as
   the fixtures rather than synthesizing analogues, so the tests pin the real defects.
5. **D5 — documentation.** Add both classes to the `ext-self-review-plan-marshall` candidate-class
   table with their detection shape and their false-positive posture.

Five deliverables — under the split guard.

## ⚠ Deliberately NOT in scope

The sender's third proposal — *make the self-review lens read the plan's own contract doc for its stated
invariants and check the diff against them* — is **excluded**. It is a semantic/LLM-judgement capability,
not a deterministic candidate class, and folding it in would change this plan's character from
"two mechanical detectors" to "an invariant-extraction engine". ⛔ If it is wanted, it is its own plan.
Recorded here so a later reader does not re-derive the omission as an oversight.

## Claim Labels

- **OBSERVED** (first-party, PR #1067 artifacts): findings `8da924` and `3e04a8`, both rated Major, both
  `resolution: fixed` via TASK-011 and TASK-013 — `artifacts/findings/pr-comment.jsonl`.
- **OBSERVED**: `status.json` `phase_steps[6-finalize].pre-submission-self-review` records
  `self-review clean: 117 candidates examined, no check matched`; `logs/decision.log:61,63` record the
  two candidate-count gate entries (115 then 117).
- **OBSERVED**: `artifacts/findings/qgate-3-outline.jsonl` finding `5872bf` — the original
  duplicate-coordinate catch, i.e. the same archetype caught one layer down by a different gate.
- **HYPOTHESIS**: `ext-self-review-plan-marshall`'s candidate classes are enumerated in one registry that
  a new class can be added to without touching the dispatch path — confirm/refute at the skill's
  candidate-class registry symbol (verify-at-outline). **Load-bearing**: if each class is hand-wired,
  D1/D2 cost changes materially.
- **HYPOTHESIS**: D1's shape (`dict[k] = v` inside a loop with no membership test) is narrow enough to
  avoid firing on ordinary accumulator code — confirm/refute by D3's population derivation
  (verify-at-outline). ⛔ **This is the plan's main risk**: a detector that fires everywhere is worse
  than none, because it trains its readers to dismiss it.
- **Verify-first clause**: settle the registry hypothesis against the implementing source before scoping
  D1/D2. The skill's SKILL.md description of its candidate classes restates the intent and does not
  establish the extension shape.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/pm-plugin-development/skills/ext-self-review-plan-marshall/**` — the
  candidate-class registry and the two new detectors (verify-at-outline)
- OBSERVED: `test/pm-plugin-development/**` — detector fixtures and tests
- OBSERVED: the `ext-self-review-plan-marshall` SKILL.md candidate-class table

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: none currently staged. ✅ Disjoint from every `plan-retrospective` plan and from the
  `manage-architecture` cluster — this is `pm-plugin-development` and touches neither.
- ⚠ Adjacent to PLAN-CIS-006 (`validate-precision`), which also edits `pm-plugin-development` but a
  different skill (`tools-marketplace-inventory`). **Different skill, different scripts — pairing is
  permissible, but re-verify the file sets at emit time before pairing them.**
- Adjacent to PLAN-CIS-015 — the companion generalisation *a stated invariant is not a checked
  invariant*; that plan owns the enumeration half, this one owns the invariant half. Neither touches the
  other's files.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/code-intelligence-substrate/plans/PLAN-CIS-021-self-review-cannot-see-a-duplicate-claimable-key.md"
```

## Relation to the epic

Third distinct confirmation in this project that **stating an archetype in prose — even in the very
document being written — does not prevent its recurrence.** It generalises the standing "a cited call
site is a SAMPLE, not an enumeration" rule from *enumeration* to *invariants*: **a stated invariant is
not a checked invariant.** And it is a measurement finding in its own right: `117 candidates examined`
reads as coverage and is a volume.

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
