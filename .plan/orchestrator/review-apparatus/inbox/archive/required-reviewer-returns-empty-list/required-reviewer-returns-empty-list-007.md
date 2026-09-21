envelope_version=1
sender_type=plan
sender_id=required-reviewer-returns-empty-list
epic=review-apparatus
kind=candidate-lesson
created=2026-09-05T16:41:32Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
created=2026-09-05
bundle=plan-marshall

# A correcting clause re-seeds the defect it corrects: delete instead

## Context

One PR (#1410) touching one standards document accumulated **five** instances of a single
defect archetype — a claim that outruns the evidence supporting it — and in **two** of
those instances the fix for the previous instance introduced the next one.

The chain, in order, all in
`marketplace/bundles/plan-marshall/skills/automatic-review/standards/cuioss-review-bot.md`:

1. Q-Gate `61bbb7` (self-review round 3, three issues in one finding):
   - line 53 `duplicate_prose` — a corrected vacuous guard's ORIGINAL statement survived
     unretired in the registry preamble, still asserting the opposite import.
   - line 370 `contract_drift` — `Capped at num_max_findings (5 centrally)` was the stale
     G1 value; G2 is 12.
   - line 573 `contract_drift` — "That pin is the revision the list was read against"
     overran: a SHA pin fixes the workflow FILE and hence the image REFERENCE STRING, but
     fixes image CONTENT only if that reference is a digest rather than a tag.
2. CodeRabbit inline comment `e10049` on line 520 — "the cited experiment varied `model`
   only, so 'does not reproduce as a knob effect' overstates the evidence."
3. Q-Gate `5274a8` (self-review round 4) — **the fix for (1) line 573 introduced the next
   instance.** The narrowed pin claim added a second re-check trigger ("whenever the org
   workflow's own image reference changes") that cannot fire independently: the
   paragraph's own premise makes that text immutable while the pin holds, so if the
   reference changes the pin moved and trigger 1 already fired. Meanwhile the risk it was
   added for — a tag re-point resolving to a different build with the pin unchanged —
   changes no file text and had **no** trigger at all.

`5274a8`'s own text records the count: "FIFTH instance of claim-outruns-evidence on this
PR and the second where the FIX introduced the next instance."

## Root cause

The remedy reached for by default is **additive**: when a claim is found to outrun its
evidence, the author appends a qualifying clause that narrows it. That move preserves the
original sentence and adds a second one whose own scope is now the thing that can be
wrong. Each correcting clause is a fresh claim, and a fresh claim is a fresh opportunity
for the same defect — which is why the chain lengthened rather than terminated.

`5274a8`'s resolution names the terminating move explicitly and it is subtractive:

> Fixed by DELETION plus recording the gap as unclosable from this checkout, not by a
> third correcting clause. ... No third correcting clause was added; per the self-review's
> remedy, adding one is what re-seeds the next round.

The same shape appears in `61bbb7`'s line 53 fix ("deleted the stale fail-closed clause,
kept the factual declaration, **no correcting paragraph added**") and its line 370 fix
(replaced the bare stale number with a deferral to the table that owns it, "restating NO
number so it cannot go stale again").

So three distinct terminating moves were found, and all three are the same move:

| Move | Applied at |
|---|---|
| Delete the over-reaching text and record the gap as open | `5274a8` |
| Delete the stale statement rather than adding a correction beside it | `61bbb7` line 53 |
| Replace the restated value with a POINTER at the source that owns it | `61bbb7` line 370 |

## Cost

The chain cost four finalize loop-back iterations
(`status.metadata.loop_back_iteration: 4`). `pre-submission-self-review` fired six times
with two `failed` outcomes among its firings, and its terminal firing reports
`self-review clean: 32 candidates examined, no check matched` — a clean terminal signal
that says nothing about the four rounds it took to reach it.

## Proposed action

1. State in the self-review remedy guidance that the FIRST remedy for a claim that
   outruns its evidence is **deletion or a pointer**, not a qualifying clause, and that
   adding a correcting clause is the move that re-seeds the archetype. The three
   terminating moves above are the concrete menu.
2. When a risk genuinely cannot be closed from the current checkout, record it as an OPEN
   GAP with the reason it is unobservable — rather than inventing a trigger that reads as
   coverage but cannot fire. `5274a8` did exactly this and that is where the chain ended.
3. Consider making a self-review round that fixes a finding in the SAME paragraph as a
   prior round's finding a flagged pattern, since that adjacency is what both re-seeding
   instances looked like from the outside.

## Evidence

- Q-Gate `6-finalize` `61bbb7` — improvement, `fixed`, three issues in one finding
- Q-Gate `6-finalize` `5274a8` — anti-pattern, `fixed`, "FIFTH instance ... second where the FIX introduced the next instance"
- finding `e10049` — CodeRabbit inline comment, `fixed`, same archetype from an external reviewer
- `status.metadata.loop_back_iteration: 4`; `pre-submission-self-review` `firing_count: 6` with prior firings `done, done, failed, done, failed`
