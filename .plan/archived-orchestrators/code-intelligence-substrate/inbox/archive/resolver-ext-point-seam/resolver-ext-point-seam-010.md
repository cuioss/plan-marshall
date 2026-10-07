envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T15:20:54Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
title=A plan that fixes an ambiguity archetype at one layer reintroduces it one layer up in the code written to fix it

# A plan that fixes an ambiguity archetype at one layer reintroduces it one layer up

Found by CodeRabbit on PR #1067 at HEAD `371854d14`; surfaced here by
`plan-retrospective` because the *pattern* of the recurrence is the reusable content, not
the individual fixes (which all landed).

## The setup — the plan learned the lesson

At `3-outline`, the Q-Gate raised an `under_coverage` finding against deliverable 4. Its
substance was not a file list: it identified that the Maven fixture tree contains two
modules declaring the same `com.example:auth-service` coordinate, and that the join being
re-homed keys a plain dict on the `groupId:artifactId` string with **last-write-wins**
semantics, so one module is silently dropped and every edge pointing at it is lost. It
warned that the planned characterization test would *pin the defect as expected*.

The plan absorbed this correctly and thoroughly. The shipped
`ext-point-derivation-resolver.md` states the obligation generically:

> a resolver whose identity key is claimed by two distinct modules MUST NOT resolve the
> collision by insertion order — it emits no edge for that key and reports it.

## The recurrence — and then it did the same thing one layer up

CodeRabbit's review of the resulting code found (finding `8da924`, rated Major):

> A truthy non-string ID such as `1` is admitted and can make the mixed `str`/`int` sort
> fail, aborting graph queries. **Two distinct resolvers returning the same string ID also
> collapse into one producer identity downstream.**

`discover_derivation_resolvers()` appended resolver ids behind a bare falsiness check. The
identical ambiguity archetype — two claimants, one key, silent last-write-wins — recurred
**at the resolver-identity layer, in the code written to eliminate it at the module-coordinate
layer**, in a document that states the general rule three sections earlier.

A second instance in the same review (finding `3e04a8`, rated Major):

> `merge_resolver_edges()` drops self-edges and unknown endpoints without adding `notes[]`;
> the resolver can therefore report `status: ok`, zero edges, and no suppression reason.

That is a **vacuous confident zero** — inside the plan whose entire stated purpose is
anti-vacuity, and whose own contract doc mandates `notes[]` as the required channel for any
condition that suppresses an edge. The plan reproduced its own target defect.

## Why this is worth recording

The plan's own Overview flagged the enumeration trap. The Q-Gate caught it once. The
contract doc states the general rule. `pre-submission-self-review` ran twice and examined
**117 candidates** at that HEAD, reporting `self-review clean: no check matched`. None of
that prevented the recurrence one abstraction level up.

This is the third distinct confirmation in this project that **stating an archetype in
prose — even in the very document being written — does not prevent its recurrence**. It
generalizes the existing "a cited call site is a SAMPLE, not an enumeration" lesson
(inbox message 002) from *enumeration* to *invariants*: a stated invariant is not a
checked invariant.

## Root cause

`ext-self-review-plan-marshall` surfaces deterministic candidate pairs (regexes,
symmetric-pair functions, flag-guard pairs, producer-consumer pairs, source-of-truth
duplicates). It has no detector for **"this change introduces a new keyed collection whose
key can be claimed twice"**, nor for **"this function has a discard path with no
corresponding report path"** — which is exactly the shape both CodeRabbit findings share.

## Proposed action

1. Add a self-review candidate class: **new dict/set keyed on a caller-supplied identity**
   → require an explicit duplicate-key disposition at the insertion site. Deterministic and
   mechanically detectable (a `dict[k] = v` or `.append` on an identity-bearing collection
   inside a loop, with no prior membership test).
2. Add a companion class: **a discard/skip/continue branch inside a function that returns a
   report channel** (here `notes[]`) → require the branch to write to that channel. This is
   the mechanical form of the anti-vacuity rule the project already states in prose, and it
   would have caught `merge_resolver_edges()` directly.
3. Standing rule for the epic: **when a plan's stated purpose is to eliminate an archetype,
   the plan's own diff is the highest-prior surface for that archetype.** Consider making
   the self-review lens read the plan's own contract doc for its stated invariants and
   check the diff against them specifically.

## Evidence

- `artifacts/findings/qgate-3-outline.jsonl` finding `5872bf` — the original
  duplicate-coordinate catch and its resolution text.
- `artifacts/findings/pr-comment.jsonl` findings `8da924` and `3e04a8` — the two Major
  recurrences, both `resolution: fixed` via TASK-011 and TASK-013.
- `status.json` `phase_steps[6-finalize].pre-submission-self-review` — `self-review clean:
  117 candidates examined, no check matched`.
- `logs/decision.log:61,63` — the two self-review candidate-count gate entries (115 then
  117 candidates).
