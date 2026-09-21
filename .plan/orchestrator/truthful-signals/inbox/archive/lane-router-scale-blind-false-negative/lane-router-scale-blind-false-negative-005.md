envelope_version=1
sender_type=plan
sender_id=lane-router-scale-blind-false-negative
epic=truthful-signals
kind=candidate-lesson
created=2026-07-30T18:49:47Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
bundle=pm-plugin-development

# Before grading a count in prose, decide whether it counts the SYSTEM or the FILE'S OWN COVERAGE

Pre-submission self-review ran 4 passes and found 9 real defects on this plan — it
comfortably earned its keep. Two of its behaviours are worth recording because they are
the *same* underlying difficulty seen from both sides.

**Pass 2 flagged a CORRECT coverage claim as stale.** The prose stated a count; the
reviewer compared it against the system-wide population, found a mismatch, and reported
the number as out of date. But the number was counting *the file's own coverage* — how
many items this document covers — not the system total. Acting on the finding would have
edited a true statement into a false one and **manufactured a false coverage claim** —
precisely the failure class the stale-count detector exists to prevent.

**The same pass missed a genuinely stale count two lines below its own finding.** So the
detector was not simply over-eager; it was applying the wrong referent, which made it
both false-positive above and false-negative below.

## Solution

When grading any count in prose, resolve the referent **first**, before comparing
anything:

1. Does this number count **the system** (how many X exist in the repo / the population)?
   Then the system-wide sweep is the oracle and a mismatch is a real staleness finding.
2. Does this number count **the file's own coverage** (how many X *this document*
   addresses)? Then the oracle is the document itself, and a mismatch with the system
   total is expected and carries no defect.

If the referent is ambiguous from the sentence alone, that ambiguity is itself the
finding — report "referent unclear, cannot grade" rather than picking one and asserting
a verdict. A wrong-referent verdict on a count is not a harmless false positive: acting
on it writes a false claim into the document.

Corollary for the reviewer: a stale-count finding should always state which oracle it
used, so the consumer can check the referent before applying the edit.

## Impact

Applies to the `stale count-prose` candidate surface in
`ext-self-review-plan-marshall`, and to any human or bot review of numeric claims in
documentation. Also a data point that self-review's value is real (4 passes, 9 defects)
and that its findings still require the same referent-checking discipline as any other
reviewer's.
