envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:54:58Z

component=manage-run-config
category=bug
created=2026-07-29

# A one-sided floor invariant reads as complete but is not

Every engine floor was documented with only a LOWER bound ("must exceed the
inner backstop"). Nothing anywhere stated the UPPER bound (must stay under the
harness ceiling once the buffer is applied), which is why a floor of 600 looked
defensible for so long even though 600+30=630 exceeds the 600s harness cap. Fixed
by documenting the two-sided invariant at all three declaration points plus a
population-derived guard test parameterised over the engine list.

## Impact

When documenting or reviewing a numeric floor/ceiling invariant, check for BOTH
bounds explicitly — a lower-only statement is easy to satisfy while silently
violating an un-stated upper bound.
