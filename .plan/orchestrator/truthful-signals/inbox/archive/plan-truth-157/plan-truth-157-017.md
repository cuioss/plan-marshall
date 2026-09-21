envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T21:01:46Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
bundle=pm-plugin-development

# A guard widened to close a vacuity defect re-opened it: the added token matched inside the target it was meant to qualify

The fix for the overfit `_AFFIRMATIVE_RE` widened it — and added a bare `write`
alternative. But `write` is itself a member of `_FORBIDDEN_WRITE_TARGETS`. Because
the grant scan lower-cases and SUBSTRING-matches the target, the token `write`
matches inside the literal backtick-quoted `write` target (backticks are non-word
characters), so naming that one target auto-satisfies the affirmative condition.
The scan degenerated to leaf + target + no-negation for that target — exactly the
inversion the docstring said it avoids.

So a fix for a vacuous guard introduced a fresh vacuity in the same guard, one
round later.

Source record: Q-Gate finding `30e7e1`, phase `6-finalize`, defect_class
`regex_overfit`, resolution `fixed` in commit `85d8e628c`.

## Solution

Drop the bare `write` alternative, keeping `writes|writing|written`. All existing
fixtures still match without it, so the guard loses no coverage — which is the
check that should have been run when the alternative was added.

The generalizable rule: when a detector matches a VERB set and a TARGET set against
the same text by substring, the two sets must be DISJOINT as strings. Check the
intersection before widening either one. A token that appears in both makes the
conjunction self-satisfying for every text naming that target.

## Impact

This is the highest-value candidate of the round because of its shape, not its
size: the vacuous-guard archetype recurred INSIDE the fix for an instance of
itself. That shape has been observed repeatedly in this repository. The operational
consequence is that a fix for a vacuity defect needs the same adversarial review as
the original — verifying only that the original negative example is now caught is
insufficient, because it says nothing about what the widening newly admits.
