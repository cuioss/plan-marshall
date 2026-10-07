envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-13T12:23:17Z

# Three PR/review findings transferred from truthful-signals (PLAN-TRUTH-103, PR #1475)

Routed here by the standing three-way rule: PR/review subject matter goes to `review-apparatus`, and
the PR test wins outright. All three were raised first-party during PLAN-TRUTH-103's finalize
(merged as `3103e9d6afa08697d5bab159afb09727882af1bc`) and are recorded in that plan's landing record
at `truthful-signals/landings/PLAN-TRUTH-103.md`. They are **not** being actioned in truthful-signals.

- **`5cbc17` — `review_commitments` reports clear over an empty population.** The vacuous-guard
  archetype on the review-commitments path: a clean verdict that can be produced by having nothing to
  check. Needs the population published alongside the verdict.
- **`f0bd9d` — `head_sha_verified` false negative on the comment path.** The verification reports
  unverified for a head it can in fact verify when the evidence arrives via comments rather than the
  review object.
- **`10f565` — `unproven_bots` includes optional bots.** An optional bot that never looked is counted
  as unproven, which conflates "required and missing" with "optional and declined". On PLAN-TRUTH-103
  `sourcery` refused all four rounds on a 7-day diff-character quota and never looked, while its green
  check remained a check-level pass.

## Two corroborating observations from the same run, for this epic's corpus

These are evidence, not separate findings — file or discard as this epic judges.

1. ⛔ **Participation must be read from comment bodies, never from the green check.** Rounds 2 and 4
   were **edit-only publishes where the review object stayed stale**, so a check-trusting run would
   have read non-participation on a round that did participate. This run verified from bodies every
   round and converged correctly.
2. ⭐⭐ **Multi-round review caught what no single pass could.** Finding `3c3297` was the round-1
   Major's own fix re-introducing the identical mirrored-set archetype one layer down. Neither a
   single gate pass nor a single review pass could have seen it. All 4 escapes partitioned
   `gate_addressable`, 0 structural — every one an archetype `ext-self-review-plan-marshall` already
   enumerates, and two of them in `test/`, past two self-review firings.

## One cross-epic dependency worth knowing

`265638` (retained in truthful-signals) records that **the loop-back counter is shared across tiers**:
a 6-round self-review consumed all 5 iterations before any external review ran, and handling
CodeRabbit's findings required raising the ceiling twice. The better the self-review performs, the
more likely it starves the external review tier. That is a structural incentive inversion affecting
this epic's subject matter even though the counter itself is not a review-apparatus surface.
