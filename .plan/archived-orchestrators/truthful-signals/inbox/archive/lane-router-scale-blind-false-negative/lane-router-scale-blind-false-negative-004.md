envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:49:41Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
bundle=pm-plugin-development

# A reviewer's occurrence count is a SAMPLE, not an enumeration — and you cannot tell which you got without sweeping

Self-review round 1 reported "3 of 8 sibling occurrences" for a rename. A content sweep
found the true population was **17** — the stated denominator understated reality by
half. Round 2's count on a different surface was accurate.

Two facts have to be held together here, and the second is the one that makes this
lesson worth filing:

- **The fix was right.** Every occurrence the reviewer *did* name was correctly handled,
  and the misses were complete — nothing half-done. Acting on the reviewer's list
  produced correct edits.
- **The population was still wrong by 2x.** So "the fix was correct" carried no
  information about "the sweep was complete", and a reader who took the `8` as the
  denominator would have believed the surface was fully covered when 9 occurrences were
  untouched.

Round 1 was a sample; round 2 was an enumeration; both were reported in the same
confident form, with a specific integer denominator. **There is no signal in the report
itself that distinguishes them.**

## Solution

- Treat any occurrence count in a review finding as a **lower bound**, never as the
  population size. Phrase it that way in the finding ("at least N", or "N found;
  population not enumerated").
- Before recording a coverage claim derived from a reviewer's count, run an independent
  content sweep to establish the denominator. The sweep is cheap; the false coverage
  claim is not.
- A reviewer that *can* enumerate should say so explicitly, so the consumer knows which
  of the two it received.

## Impact

Directly extends the standing "a reviewer's list of call sites is a SAMPLE, not an
enumeration" archetype (previously: CodeRabbit named 3 `write_status` callers against a
real count of 14). This sighting adds the sharper point: the sample can be *entirely
correct* and still understate the population, so correctness of the fix is not evidence
of completeness of the sweep.
