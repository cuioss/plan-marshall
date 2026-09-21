# PLAN-PR-016: A correct review scores as maximally wrong

epic: review-apparatus
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-08-01 from the PLAN-PR-001 / PR #1071 inbox drain (messages `-003` and `-004`),
> on an operator decision to prioritise it over queue-order PLAN-PR-010.

## Objective

PR-Agent posts a `## PR Reviewer Guide` boilerplate comment on **every** PR it reviews. That heading is
missing from PR-Agent's registry `ignore_patterns`, so the producer pre-filter that exists to drop bot
boilerplate does not match it and the comment is filed as a **pending hand-triage finding on every PR**.
Separately, the review-retrospective aggregator maps `resolution: accepted` into the `false_positive`
bucket — and on a clean PR that Guide comment is PR-Agent's *only* record and always closes as
`accepted`. The reviewer is therefore scored **100% false-positive / 0.0% resolved-as-fixed exactly when
it behaved correctly.**

⛔ **These two are ONE plan, not two, and the reason is not convenience — it is correctness.** They act on
the *same comment* in opposite directions. Filtering the Guide at the producer makes PR-Agent's clean-PR
record **empty** rather than one-accepted, which changes the metric defect's shape rather than fixing it,
and may flip a participation detector to non-participation. Landing either alone converts one wrong
metric into a different wrong metric.

This matters beyond tidiness: the epic's own measurement layer is the thing being corrupted. The
4-day sweep's Recommendation B — a fixed-diff charter measurement of PR-Agent — **cannot be trusted while
the aggregator inverts a correct review into a maximally-bad score.**

## Deliverables

1. **Add the `## PR Reviewer Guide` heading to PR-Agent's registry `ignore_patterns`** so the producer
   pre-filter drops it. One data row; the pre-filter already consumes the list.
2. **Stop `accepted` collapsing into `false_positive`** in the review-retrospective resolution-bucket
   mapping — either give `accepted` its own bucket ("acknowledged, no action required" is not the claim
   "the reviewer was wrong"), or exclude meta comments from the bucket denominator so a reviewer whose
   only record is meta reports as *no actionable signal* rather than *all-wrong signal*.
3. **Settle the interaction explicitly, with a test that pins it**: what a clean-PR PR-Agent record looks
   like after D1, and what the aggregator and the bot-participation detector each report for it.
4. Regression tests for the clean-PR arm and the mixed arm, each verified to fail pre-fix.

## Claim Labels

- OBSERVED: PR-Agent posts `## PR Reviewer Guide` on every reviewed PR — seen across **52 PRs** in
  [`findings/2026-08-01-sweep-4day.md`](../findings/2026-08-01-sweep-4day.md); the body is a meta status
  summary, not an actionable remark.
- OBSERVED: the aggregator maps `accepted` → `false_positive`, producing `pct_resolved_as_fixed: 0.0` on
  a clean PR — first-party report from the PLAN-PR-001 finalize
  (`finalize-step-review-retrospective`), inbox `-004`.
- OBSERVED: PR #1071's `review-retrospective` step reported `1 reviewer, 0 actionable`.
- HYPOTHESIS: the Guide heading is absent from `ignore_patterns` — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md` § the registry
  record's `ignore_patterns` list (verify-at-outline).
- HYPOTHESIS: the resolution-bucket mapping lives in the project-local
  `finalize-step-review-retrospective` skill and/or the per-reviewer metrics pass it drives —
  confirm/refute by locating the symbol that assigns `false_positive` (verify-at-outline).
  ⚠ The orchestrator has NOT read that implementing source; the mapping is a first-party report.
- **Verify-first clause** — ⛔ **Before scoping D1, settle what an EMPTY PR-Agent record produces.**
  Confirm against the implementing source whether the retrospective aggregator and the
  bot-participation detector treat an empty record as *non-participation*. If either does, D1 alone
  would turn a correct review into an apparent non-review — a strictly worse failure than the one being
  fixed — and the deliverables must be re-scoped so D2 lands first or both land together. Refutation
  loops back and re-scopes; it does not proceed.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/automatic-review/standards/pr-agent.md` —
  the registry record's `ignore_patterns` (verify-at-outline).
- HYPOTHESIS: the project-local `finalize-step-review-retrospective` skill and the per-reviewer metrics
  pass it drives — the resolution-bucket mapping symbol (verify-at-outline).
- HYPOTHESIS: the bot-participation detector, **read-only unless the verify-first clause forces a
  change** — `automatic-review/scripts/review_completeness.py` and/or
  `automatic-review/standards/bot-participation-contract.md` (verify-at-outline).
- HYPOTHESIS: tests for the producer pre-filter and the retrospective aggregator (verify-at-outline).

⛔ **Re-verify the whole surface against HEAD at outline.** This spec was staged hours after PR #1071
landed and PR-014 is in flight over `automatic-review`.

## Dependencies and Sequencing

- **Depends on**: none. ⭐ Deliberately NOT sequenced behind PLAN-PR-007 — it neither reads nor changes
  the `absent`/`stale`/refusal taxonomy.
- **Overlaps with**: ⛔ **PLAN-PR-010** — both touch `finalize-step-review-retrospective`. PR-010 is
  sequenced BEHIND this plan by operator decision (2026-08-01). **Do not pair them.**
- **Overlaps with**: ⚠ **PLAN-PR-014** (running at stage time) on `automatic-review/`. PR-014 owns
  `review_completeness.py`'s argparse surface and the invocation blocks; this plan should touch
  `review_completeness.py` **only** if the verify-first clause forces it. Re-check PR-014's landed diff
  at outline before scoping there.
- **Adjacent to**: `automatic-review/standards/coderabbit.md` / `sourcery.md` — sibling registry records
  that stay untouched. ⛔ **PLAN-PR-003** owns the CodeRabbit strip-vs-extract question; do not widen
  into it. If the pre-filter change looks like it should generalise across bots, that is PR-003's
  population, not this plan's.
- **Adjacent to**: the `post_responses` non-idempotency Open Defect — a different verb on the same
  provider, deliberately out of scope here.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/review-apparatus/plans/PLAN-PR-016-a-correct-review-scores-as-maximally-wrong.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
