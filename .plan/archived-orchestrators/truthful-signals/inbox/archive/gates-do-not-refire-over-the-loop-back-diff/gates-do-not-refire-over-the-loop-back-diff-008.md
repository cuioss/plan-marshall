envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:39Z

component=project:finalize-step-review-retrospective
category=bug

# review-retrospective maps `accepted` to `false_positive`, so the most benign reviewer behaviour earns the worst per-reviewer profile

## Observation

`review-retrospective`'s `resolution_quality` computation maps the finding resolution **`accepted`** into the **`false_positive`** bucket.

Consequence: a reviewer whose only output is a **clean, no-issues status summary** — i.e. a reviewer that read the diff and correctly found nothing wrong — accumulates `accepted` resolutions and is therefore scored as having produced **false positives**. The most benign and most desirable behaviour a reviewer can exhibit earns it the **worst possible** per-reviewer quality profile.

## Why the mapping is wrong

`accepted` and `false_positive` are semantically opposite dispositions:

- **`accepted`** — the finding was judged valid and its stated position taken into account; nothing needed changing. The reviewer was *right*.
- **`rejected`** — the finding was refuted. That is the false-positive bucket.

The corpus already has the correct home for refutation: the `rejected` resolution set by the validity-verification (`ext-point-verify`) stage exists precisely to mark a refuted finding. `accepted` is not it.

## Why this belongs to `truthful-signals`

The metric **inverts** the signal it claims to measure. Any downstream use of the per-reviewer profile — reviewer selection, bot-roster pruning, "which reviewer is worth its quota" judgements — will preferentially **remove the reviewers that are behaving correctly**. And it degrades monotonically: the cleaner a reviewer's record, the worse its computed score, so the error compounds rather than averaging out.

This intersects a live epic concern: the project has already been burned by **enabled-bots-vs-operative drift** and by pruning a bot that could still post valid findings. A metric that actively recommends pruning the *good* reviewers is a direct amplifier of that failure.

## Suggested shape of the fix

Map only `rejected` into `false_positive`. Give `accepted` its own bucket (`valid_no_action` or similar) and count it toward, not against, reviewer quality. Then re-derive any historical per-reviewer profile that was computed under the inverted mapping — the stored profiles are wrong, not just the code.

## Not actioned

Out of PLAN-TRUTH-001's scope. Handed to the epic.
