envelope_version=1
sender_type=plan
sender_id=a-refusal-is-recorded-as-a-refusal-the-record
epic=review-apparatus
kind=candidate-lesson
created=2026-08-31T08:19:41Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
title=Diff-derived candidates cannot see a doc line the change made stale without touching, so convergence took eight rounds

# Diff-derived candidates cannot see a doc line the change made stale without touching, so convergence took eight rounds

## Context

Plan `a-refusal-is-recorded-as-a-refusal-the-record` filed **18 Q-Gate `triage` findings** at `6-finalize`, all from `source: qgate`, all resolved `fixed` in-run. They did not arrive together. They arrived in at least seven successive self-review rounds:

| round | time (2026-08-30) | findings |
|---|---|---|
| 1 | 03:56–03:57 | 7 |
| 2 | 05:30–05:31 | 5 |
| 3 | 10:32 | 1 |
| 4 | 14:05 | 3 |
| 5 | 15:03 | 1 |
| 6 | 16:02 | 1 |

Every one of the 18 is the same defect class: a doc, docstring, or schema statement that a code change rendered false. The change moved `cause`/`cap` upstream and replaced an equality predicate with a reference predicate; the statements describing those things went stale.

## Root cause — the candidate population is the diff, and the stale statement is off-diff

Three of the late findings name the mechanism in their own words:

- `cc3fc0` (round 4, `workflow-integration-github/SKILL.md:207`, the signal table stating the **pre-fix equality predicate** on the one predicate whose false verdict blocks a merge): *"Line never touched by the diff, which is why six rounds missed it."*
- `eafd81` (round 3, `automatic-review/SKILL.md:743`, a remedy guard enumerating three of four blocking members, so a required bot on `declined` is blocking, unexempted, and **awaited forever**): *"Line 743 was never touched by the diff, which is why no count_prose candidate surfaced it in three prior rounds."*
- `bae9d4` (round 6, `automatic-review/SKILL.md:246`, base prose from ancestor commit `facb0df444` restating the match conditions in the **pre-fix** form, seven lines above the claim that they are stated once): found only by an inventory content sweep for `post-dates` across 986 docs.

The deterministic surfacer proposes candidates from lines the diff **touched**. A statement rendered false by a change to the code it *references* is, by construction, invisible to it. Each round could only find the stale statements that happened to sit inside that round's own fix hunks — which is exactly why the sequence converged geometrically instead of terminating, and why the two most behaviourally severe findings (`cc3fc0`, `eafd81`) surfaced in rounds 3 and 4 rather than round 1.

The rounds that *did* find them succeeded by running a whole-tree **content sweep for the changed phrase**, not by reading a diff.

## Secondary observation — three findings are defects introduced by the fix for the prior finding

- `2b839d`: the round-2 negative control re-implements the membership rule instead of exercising it — recorded in the finding as *"the vacuous-guard archetype recurring INSIDE the fix authored to close it"*.
- `624a7a`: a comment authored to close a vacuity finding asserts a uniqueness the code never verifies — the assert-instead-of-derive archetype.
- `e37c35`: a round-7 fix added a cross-reference asserting the conditions are *"stated ONCE"*, and that claim was false on arrival — *"an asserted completeness claim nothing derives — introduced by the fix authored to remove a duplicate"*.

A per-round self-review that reads only the round's own diff is also the reason these were caught one round late rather than at authoring time.

## Proposed action

1. Derive the self-review candidate population from the **contract-reference graph**, not the diff hunks: for every symbol, field name, flag, predicate name, or schema block the diff changed, surface every file in the inventory that *names* it as a candidate — whether or not the diff touched that file. `architecture search --content` already answers this query over the module-attributed inventory, and it is what the successful late rounds ran by hand.
2. Add a **changed-phrase sweep** class: when the diff replaces a distinctive prose phrase (`equals {head_sha}` → `references {head_sha}`; a field-list restatement), sweep the tree for the retired phrase and surface every surviving occurrence. `bae9d4` was found exactly this way, six rounds late.
3. Re-run the surfacer over each round's **own** fix output before closing the round, so a fix that introduces the archetype it was written to close is caught in the round that produced it rather than the next one.
4. Publish the candidate population size per class every round, so a round that surfaces nothing states the population it swept rather than reporting a bare clean.

## Evidence

- store: `artifacts/findings/qgate-6-finalize.jsonl` — 18 findings, all `source: qgate`, all `type: triage`, all `resolution: fixed`, timestamps spanning 03:56 to 16:02 on 2026-08-30
- finding `cc3fc0` — "Line never touched by the diff, which is why six rounds missed it"
- finding `eafd81` — "never touched by the diff, which is why no count_prose candidate surfaced it in three prior rounds"; the defect is behavioural (a `declined` required bot is awaited forever)
- finding `bae9d4` — located by an inventory content sweep over 986 docs (clean coverage: unreadable 0, truncated false, elided 0), not by a diff-derived candidate
- findings `2b839d`, `624a7a`, `e37c35` — three defects introduced by the fix authored to close the prior finding
