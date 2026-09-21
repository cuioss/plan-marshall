envelope_version=1
sender_type=plan
sender_id=plan-footprint-is-unknowable-to-its-own-graders
epic=truthful-signals
kind=candidate-lesson
created=2026-08-27T15:05:15Z

component=pm-documents:ref-documentation
category=anti-pattern
confidence=high
source_plan=plan-footprint-is-unknowable-to-its-own-graders
source_pr=1359

# A doc-contract fix that RESTATES its authority reproduces the drift - delete and point

## Context

This run's self-review filed 8 Q-Gate findings in `6-finalize`. **7 of the 8** are one
family: a document restating a fact whose authority lives elsewhere, and the restatement
having gone stale or over-claimed. In **7 of those 7**, the fix that was actually applied
was **deletion of the restatement plus a pointer to the authority** - never a corrected
restatement.

That convergence is the lesson, and it is not the same lesson as the two sibling
candidates already filed from this plan (see § Relation to already-filed candidates).

The sharp edge is one member of the set. In `c0c0d5`, TASK-14 *did* replace an inline
four-code enumeration with a cross-reference to the authoritative error set - and made the
defect **worse**, because it kept the false half of the sentence and thereby bound
"the refresh derived nothing" to the full error set *including any code added later*. A
cross-reference is a fix only when the restated content is **removed**. Re-anchoring a
retained restatement to an authority propagates the error to everything that authority
subsequently gains.

## Root cause

A restatement is a second source of truth with no update path. Correcting its *content*
leaves the second source in place, so the next change to the authority re-opens the same
gap - and if the correction re-anchors the restatement to the authority without deleting
it, the gap widens from a fixed set to a growing one.

The four-times-in-one-run recurrence is the observable consequence: every fix in this
class that was authored as a *rewrite* either re-introduced the class or shipped a new
instance of it.

## Proposed action

State it as an authoring rule for doc-contract fixes, in `ref-documentation` alongside the
existing "cross-reference instead of duplicating" standard, and make it the expected
resolution shape for the `contract_drift` / `source-of-truth duplicates` classes:

> When a document restates a fact owned elsewhere and that restatement is wrong or stale,
> **delete the restatement and name the authority**. Do not correct it in place, and do not
> attach a cross-reference to a restatement you are keeping - a retained restatement bound
> to an authority inherits every future member of that authority's set.

Two bounds worth stating with it, both derived from this same substrate rather than
assumed:

1. The rule governs **duplicated content**. The 8th finding (`655324`,
   `same_document_contradiction`) was a *missing* pointer, not a duplicated one, and its
   correct fix was an addition. Deletion is the remedy for restatement, not a universal.
2. A restatement is legitimately kept only when it carries independent value the authority
   does not. In `5bd6af` the docstring note cross-referenced the very section it was
   restating - zero independent value - which is what made deletion obviously right.

## Evidence

Substrate: `manage-findings qgate list --plan-id plan-footprint-is-unknowable-to-its-own-graders
--phase 6-finalize` - `total_count: 8`, `filtered_count: 8`, i.e. the complete phase
population, not a sample.

| hash_id | Site | Restated fact | Applied fix |
|---|---|---|---|
| `28c3a7` | plan-retrospective/SKILL.md:201 | 4-tier resolver chain (code has 5) | replaced enumeration with pointer to `RESOLVING_TIERS` |
| `f54406` | plan-retrospective/SKILL.md:211 | same chain, 4 tiers | replaced enumeration with pointer |
| `bcdd97` | plan-retrospective/SKILL.md:500 | same chain, 3 tiers | dropped enumeration ("walks its full declared tier chain") |
| `8caccf` | q-gate-validation.md:836 | "nothing was derived and nothing was written" | **deleted** "nothing was derived and" |
| `c0c0d5` | phase-6-finalize/SKILL.md:1477 | same claim, re-anchored by cross-reference | **deleted** the false half |
| `029ef1` | phase-4-plan/SKILL.md:721 | same claim, `not_a_list` named inside the set it contradicts | **deleted** the false half |
| `5bd6af` | manage-references.py module docstring | note restating SKILL.md § Enforcement | **deleted** the note (restatement with no independent value) |

7 of 7 resolved by deletion-plus-pointer. The findings' own resolution text names the
convergence three separate times: *"Convergent fix is DELETION, not rewriting"* (`8caccf`),
*"Same convergent deletion"* (`c0c0d5`, `029ef1`), *"Applied the convergent DELETION rather
than relocating the note"* (`5bd6af`).

Recurrence inside the class:

- `8caccf` resolution: *"This was a REGRESSION my own TASK-14 fix introduced."*
- `c0c0d5`: the cross-reference-without-deletion widening described above.
- `5bd6af` resolution: *"This is the third occurrence in this run of a fix introducing the
  defect class it was fixing."*
- A fourth escaped this phase entirely: D7's new `outline-vs-shipped.md` § Persistence
  copied a sibling's broken `--diff-file work/footprint.txt` capture command into new text
  (filed separately as candidate `-001`), so the newly shipped aspect exits 1 when its
  documented command is run verbatim.

## Relation to already-filed candidates

Deliberately not a duplicate of the two neighbours this plan already filed:

- **`-002`** (`pm-plugin-development:ext-self-review-plan-marshall`) proposes a **detection**
  mechanism - re-run the class surfacer over the fix's own diff before closing a round. It
  says nothing about how the fix should be authored, and its remedy catches the recurrence
  after the fact.
- **`-001`** (`plan-marshall:plan-retrospective`) is one **instance** (the `work/footprint.txt`
  dangling reference), not the class.

This candidate is the authoring rule that would prevent the class, and it carries the one
finding neither neighbour states: a cross-reference attached to a *retained* restatement is
not a fix but an amplification.
