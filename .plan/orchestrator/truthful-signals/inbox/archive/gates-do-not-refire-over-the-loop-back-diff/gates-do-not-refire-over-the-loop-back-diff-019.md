envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:50:57Z

component=plan-marshall:automatic-review
category=improvement

# Review-bot verdicts need the head-dependence discriminator this plan just built for finalize steps

## Observation

PLAN-TRUTH-001 closed this defect class for finalize steps: *a verdict computed against a superseded HEAD must not stand as a verdict for the current one.* The discriminator it introduced is "would this verdict change if HEAD changed?", and it derived a 9-member head-dependent population over all 25 registered steps.

**The same defect occurred, in the same run, one layer up — and was resolved by an operator override.**

From `decision.log`:

> `[WARNING]` Pre-merge review-completeness barrier **OVERRIDDEN** by operator. Required bot `pr-agent` has not reviewed post-force-push HEAD `43ed04ccb2f345621e04648c8da8b18d1192fafc` — **its Reviewer Guide was posted against the pre-rebase head**. `coderabbit` re-fired but is rate-limited with a 21 minute window, `sourcery` is weekly-quota refused. Merging with the required bot participation **UNPROVEN** against the merged tree.

And an hour earlier, at the bot gate:

> `[WARNING]` Operator chose **PROCEED UNREVIEWED**. PR 1073 is CI-green but no bot read the diff — `pr-agent` posted only a participation Guide, `coderabbit` refused `awaitable_window`, `sourcery` refused `hard_quota`. Quorum passed only because both refusers are `optional_bots`. **This green proves participation, not review.**

Apply the plan's own discriminator to a review bot: *would a bot's review verdict change if HEAD changed?* Trivially yes — the review is a function of the diff. So every review bot is head-dependent by the exact test the plan formalized. Yet no derivation, no `head_at_completion` stamp, and no invalidation-on-force-push exists on that side. The barrier detected the staleness and then had to be overridden by hand, twice in one run, because the machinery to re-fire does not exist.

**The finalize steps and the review bots now sit on opposite sides of the same rule.** After #1073, a `ci-verify` green recorded against a HEAD that a force-push superseded is automatically invalidated. A `pr-agent` Reviewer Guide posted against a HEAD that the same force-push superseded is not — it remains the recorded participation evidence, and the only thing standing between it and a merge is an operator reading a WARNING.

## Root cause

Head-dependence was modelled as a property of *finalize steps* — a frontmatter fact on `ext-point-finalize-step` implementations. Review-bot participation is tracked through a different surface (`ci pr comments`, per-bot completion state) that has no equivalent fact and no HEAD binding at all.

The two surfaces answer the same question — "is this recorded verdict still about the current tree?" — and only one of them can answer it.

## Proposed action

1. Stamp a `head_sha` on every recorded bot-participation event, so a review verdict carries the HEAD it was computed against exactly as a finalize step's outcome now does.
2. Invalidate recorded participation when HEAD is superseded by a force-push, rebase, or loop-back commit — the same three triggers the plan's D3 enumerates for steps. A required bot's participation recorded against a superseded HEAD must read as *unproven*, not as *satisfied*.
3. Make the pre-merge barrier's own verdict head-scoped, so overriding it is a decision about a specific stale HEAD rather than about the barrier as a whole. Today the override is all-or-nothing.
4. Note for the corpus: the standing rule is *only `ci pr comments --pr-number N` is evidence of participation*. This run adds a second clause — **participation evidence is only evidence for the HEAD it was posted against.** A comment from a bot is not a review by it, and a review by it is not a review of *this* tree.

## Evidence

- `logs/decision.log` 19:17:08Z `[WARNING]` — pre-merge barrier overridden; `pr-agent` Reviewer Guide posted against the pre-rebase head
- `logs/decision.log` 18:58:03Z `[WARNING]` — PROCEED UNREVIEWED at the bot gate; "This green proves participation, not review"
- aspect: chat_history_analysis — `operator_gate_dispositions[2]`, both recorded only in `decision.log`, neither surfacing as a conversational turn
- `status.metadata.phase_steps["6-finalize"]["automatic-review"]` — `head_at_completion: 3dcfab234e...`, i.e. the STEP is head-stamped while the bot verdicts it collected are not
- Deliverable 3 of PR #1073 — force-push invalidation of a recorded `ci-verify` green (`test_ci_verify.py`), the exact mechanism absent on the review side
- Related but distinct: epic inbox message 009 records that no bot read the diff; this message records that even the participation that WAS recorded was scoped to a superseded HEAD
