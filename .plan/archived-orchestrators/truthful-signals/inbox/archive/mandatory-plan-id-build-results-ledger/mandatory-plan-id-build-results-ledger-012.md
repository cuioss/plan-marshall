envelope_version=1
sender_type=plan
sender_id=mandatory-plan-id-build-results-ledger
epic=truthful-signals
kind=finding
created=2026-08-01T21:28:22Z

## Finding: the review-retrospective aggregator cannot represent a REFUSAL

**Observed in**: main, during finalize of `mandatory-plan-id-build-results-ledger`.
**Scope**: outside every deliverable of this plan. Deliberately NOT fixed here.
**Routing**: this is a **review-participation** defect, so by the three-way routing rule it
belongs to `review-apparatus`, not to `truthful-signals`. It is emitted here because the
epic inbox is the only channel an executing plan may write to — please forward it via the
INBOX rather than actioning it locally.

### What was observed

The `project:finalize-step-review-retrospective` step recorded:

```text
1 of 3 bots reviewed with 0 actionable, 2 refused, sonar zero vacuous
```

Behind that display string, the aggregator's own structured output carried
`reviewer_count: 1`, because the aggregator **counts reviewers that filed**. Two bots that
were configured, invoked, and **refused** are structurally invisible in the count.

Separately, the aggregator bucketed a reviewer that *participated but reported nothing*
as `false_positives_count: 1`.

### Why it matters — two distinct defects

**1. A refusal has no representation.** `reviewer_count: 1` reads as *a single-reviewer
setup*. The actual state was *a 3-reviewer setup experiencing a 2-reviewer outage*. Those
are opposite conclusions about review coverage drawn from the same number: the first says
"this is how much review this repo does", the second says "this repo's review capacity
was 67% down for this PR". A count that cannot tell them apart cannot support any
coverage judgement.

This is the same shape as the standing rule that *only* `ci pr comments --pr-number N` is
evidence of participation, and that a green finalize is not proof the bots saw the diff —
here the aggregator is doing exactly the thing that rule forbids, one layer up.

**2. "Participated but reported nothing" bucketed as a false positive is a category
error.** A reviewer that ran and found nothing produced a *true negative* (or, more
precisely, an empty true result). Filing it under `false_positives_count` corrupts the
per-reviewer quality metric in the direction of making a clean reviewer look noisy, which
is the opposite of the truth and will mis-rank reviewers if the metric is ever used to
tune the roster.

### Suggested shape of a fix (not implemented)

- Give the aggregator an explicit per-reviewer **participation state** —
  `filed` / `participated-empty` / `refused` / `not-invoked` — and derive `reviewer_count`
  from the invoked roster, not from the filed set.
- Report outage explicitly (`refused_count`, `expected_reviewer_count`) so a degraded run
  is loud rather than arithmetically indistinguishable from a smaller roster.
- Move "participated, reported nothing" out of `false_positives_count` into its own
  bucket; a false positive requires a *filed* finding that was wrong.
