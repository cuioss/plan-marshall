envelope_version=1
sender_type=plan
sender_id=prq-06-a-lane-override-that-cannot-take-effect-is
epic=post-run-quality
kind=candidate-lesson
created=2026-09-19T18:46:04Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern

# Round N's fix produced round N+1's finding — the self-review seeded a measurable share of its own findings

The pre-submission self-review ran ten rounds on this plan. At least two of its sixteen fixed findings were **created by the immediately preceding round's own fix**, which means part of the loop's cost was spent cleaning up after itself.

## Evidence (both 6-finalize, both `fixed`)

- `6681fd` — "The fenced text block presented as the verbatim refusal message **was rewritten by round 1's edit** while the emitting code (`_cmd_quality_phases._inert_off_refusal`) was not touched and still returns 'Set a tier (minimal/standard/full) instead'. The doc quoted an error string the product never prints." Round 1 fixed a contract drift by editing the doc, and thereby created a fresh contract drift between the doc and the emitter.
- `94a52a` — "**Round 1 swapped 'core'->'seeded' on adjacent prose lines** but left the referent's own identifier `_SEVEN_CORE_STEPS` unrenamed at its declaration and use sites, so line 1198 read `for seeded in _SEVEN_CORE_STEPS` — naming the same set by two contradicting words on one line."

Both are the same shape: a fix that changed ONE of two co-referring sites, converting an agreement into a disagreement.

## Rule

A fix for a consistency finding must be applied to the **co-reference set**, not to the site the finding cites. Before editing a quoted string, a count, or a name, ask what else states the same fact — the emitter behind a quoted message, the identifier behind renamed prose, the sibling doc with the duplicated block — and edit or verify all of them in the same change.

The strongest form of this fix is structural: `6681fd`'s real remedy is not to re-quote the string more carefully but to stop restating the emitter's output in prose at all.

## Why this is worth the epic's attention

The retrospective separately measured that 6-finalize consumed 50% of the plan's 8.44M tokens across 47 step firings, with `pre-submission-self-review` firing 9 times and 7 of its 8 prior firings returning `loop_back`. This finding supplies part of the MECHANISM behind that number: some of those rounds existed because earlier rounds' edits were under-scoped. Self-seeded findings are a cost multiplier on a step already identified as the plan's dominant expense.
