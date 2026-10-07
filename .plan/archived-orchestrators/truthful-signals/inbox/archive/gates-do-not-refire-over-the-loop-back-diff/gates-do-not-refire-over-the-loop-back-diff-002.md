envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:01Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# When a documented count and its enumeration disagree, DERIVE the population — never reconcile the numeral down to the list

## Observation

PLAN-TRUTH-001 needed the set of head-dependent finalize steps. The spec carried both a numeral ("nine / three") and a hand-maintained enumeration. They disagreed: the enumeration listed eight.

The reflexive repair — trust the list, correct the numeral from nine to eight — would have **shipped the target defect**. Deriving the population over all 25 registered finalize steps from the live registry returned **9 head-dependent / 16 not**, and identified the missing ninth member as `project:finalize-step-era-stamp-fill`. The numeral was right; the list was stale.

## Why the reflex is wrong

A numeral and a list decay by different mechanisms and at different rates:

- A **list** decays silently on every addition to the population. Whoever adds member N+1 has no reason to visit a distant doc's enumeration, so drift is the default outcome.
- A **numeral** decays only when someone edits it, which is a deliberate act.

So the list is the more likely of the two to be stale, and "the list is concrete, the number is just prose" inverts the actual reliability ordering. Worse, reconciling the numeral to the list is a **silent, self-consistent** repair: afterwards the document agrees with itself and the missing member is no longer detectable from the document at all. The disagreement was the only surviving evidence of the drift, and the repair destroys it.

## Rule

When a count and an enumeration of the same population disagree in a document:

1. **Do not reconcile them against each other.** Neither is the authority.
2. **Derive the population from the live source** (the registry, the manifest, the filesystem) over the *whole* candidate set — not just over the listed members.
3. Correct **both** the numeral and the enumeration from the derivation, and prefer replacing the hand-maintained enumeration with a derivation so the class of drift cannot recur.
4. A derivation that only visits the already-listed members re-derives the list, not the population. The candidate set must be the full registry.

## Detection

A doc-vs-doc reconciliation that changes a count to match a nearby list, with no live-source query in the same change, is the signature. Treat it as a finding, not a cleanup.
