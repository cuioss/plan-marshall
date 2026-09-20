envelope_version=1
sender_type=plan
sender_id=absent-names-two-states-with-opposite-remedies
epic=review-apparatus
kind=candidate-lesson
created=2026-08-08T20:43:15Z

# Candidate lesson: three self-review passes did not find what the first bot review found

**Source records:** Q-Gate findings `6fc38c`, `d26dd0`, `b0f7dc` (pass 1), `d4ebf1`, `64165f` (pass 2), `92dd7c` (pass 3), all `resolution: fixed`; versus `pr-comment` findings `212b88`, `dadd8a`, `a582b1`, `2690b3`, `b7e497`, `d66c05`, `308d72`, `7b5c4c`, `53a438` from CodeRabbit's single review of `56580bd9d`.

## The observation

Pre-submission self-review ran three passes over this diff and produced six findings. Every one of them is a **documentation-consistency** finding: a strictly-narrowing claim that was too broad, a Predicate-2 sentence that contradicted an instruction 29 lines above it, three consumer docs still asserting a retired five-member count, two sites calling the blocking subset seven when it is six, and one hard-coded guard population.

CodeRabbit's *first* review of the same diff produced 8 actionable comments of which four were Major, and they were of a different kind:

- a binary read of a fallible observable that coerces UNKNOWN into a positive (`212b88`, Major)
- a documented remedy with no reachable invocation — `not_triggered` said "generate the trigger event" with no verb, no outcome recording, no timeout branch (`dadd8a`, Major)
- an observable scoped to the head branch when its meaning is per-PR, so a reused branch or two PRs on one branch suppress the remedy (`b7e497`, Major)
- a malformed-envelope path collapsing "never read" into "read empty", contradicting the function's own docstring (`2690b3`)
- a drift pivot shared by both sides of a count comparison, so the comparison stays green over a set missing a member (`d66c05`, Major)

## The generalisable shape

Self-review found **internal inconsistencies between statements in the diff**. It did not find **behaviours of the code under inputs the diff does not contain**. Those are different search problems, and this run is a clean natural experiment on the difference: same diff, same day, six findings versus eight, essentially disjoint.

Two consequences worth the epic's attention:

1. **Self-review passing is not evidence the diff is sound.** Three green-ish passes preceded four Major findings. A run that reads self-review as a proxy for review quality will merge on that proxy exactly when a bot is unavailable — which is what happened later in this same run (see the empty-quorum candidate).
2. **Self-review's own recurring hit is the hard-coded population**, and it caught one (`92dd7c`, pass 3) while missing two more that CodeRabbit then found (`d66c05`, `308d72`) plus one more found at 6-finalize (`7bf2b7`). Five instances of one archetype in one PR, discovered by three different mechanisms — see the separate candidate on that archetype.

## Candidate remedy (not applied)

Do not converge self-review passes on the class of finding the previous pass produced. Passes 2 and 3 here produced more of pass 1's class (count prose, then a guard population) rather than reaching for the behavioural class. Whether that is a detector-coverage gap or an attention-anchoring effect is worth deciding before adding detectors.

## Why it is routed here

The relative yield of self-review versus automated bot review, and what a green self-review licenses, is `review-apparatus` policy.
