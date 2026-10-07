envelope_version=1
sender_type=plan
sender_id=daemon-baseline-interpreter-is-unregistrable
epic=truthful-signals
kind=candidate-lesson
created=2026-08-08T21:24:29Z

component=plan-marshall:workflow-integration-github
category=improvement
confidence=high
source_aspects=findings-store,review-retrospective

# Bot completion states are computed, consumed in-context, and never persisted — so "refused to review" is unrecoverable afterwards

## Context

Two channels carry review-bot participation, and only one of them survives the run.

- **Computed and used in-context**: `bot_completion` resolves a per-bot completion state. On this run it produced `refused_awaitable` for CodeRabbit and `participated_but_empty` for Sourcery and PR-Agent. The pre-merge barrier consumed those states correctly and honestly: `participation_complete=true over required_bots=pr-agent … proves=participation_only … coderabbit remains unproven (refused_awaitable)`.
- **Persisted**: the `pr-comment` findings store. It holds only comment records. On this PR it held two, both human/pipeline-authored.

Nothing writes the first channel into the second. Once the run's context is gone, the completion states are gone with it.

The consequence showed up immediately, one step later. `finalize-step-review-retrospective` reads the `pr-comment` store, found no record for any of the three bots, and correctly refused to conclude anything — its verdict is **unmeasurable**, and its single substantiated recommendation is exactly this gap:

> CodeRabbit's rate-limit refusal is reported in the dispatch context but has **no corresponding record in this plan's `pr-comment` store**. A refusal that leaves no trace in the store is indistinguishable at read time from a reviewer that had nothing to say — exactly the ambiguity this retrospective must otherwise refuse to resolve.

So a state the system successfully computed, and correctly acted on at the merge gate, became unrecoverable one step later — and the downstream consumer had to degrade to `unmeasurable` over information the run already possessed.

## Root cause

`bot_completion` is a **reporting** verb: it computes a state and returns it to its caller. The taxonomy is rich (and was recently widened — `#1118` added `stale` and `not-triggered` members), but richness in a return value that is never persisted buys nothing beyond the calling step's lifetime. The store's schema is comment-shaped, so a non-comment participation fact has no row to occupy, and an absent row is read by every downstream consumer as "nothing to say".

This is the same overload that the trigger-A skip rests on, filed alongside: an empty `pr-comment` slice is made to carry three incompatible meanings — *reviewed and silent*, *refused*, and *publishes nothing the store records* — because nothing else records participation.

## Proposed action

Persist the completion state as a first-class record keyed by `(pr_number, bot_kind, head_sha)`, written whenever `bot_completion` resolves — including, and especially, for the non-participating states (`refused_awaitable`, `not-triggered`, `stale`). It needs no new store: a `pr-comment` finding with an explicit non-comment kind, or a sibling `bot-participation` type, both give the retrospective and the merge-gate guards one substrate to read.

Then have `finalize-step-review-retrospective` read that record, so a refusal reports as a **measured non-participation** rather than as `unmeasurable`, and so a genuinely silent reviewer is distinguishable from an absent one. Downstream, the same record is the population a re-review guard should be derived from.

## Impact scope

Every plan whose PR draws a bot refusal or rate-limit. On this run the effect was contained — the operator merged on green over an explicitly accepted review-coverage gap (decision.log `309777`), a judgement made with the in-context information intact. The loss is to the durable record: the review retrospective, the archived-plan audit, and any cross-plan reviewer-effectiveness analysis all read the persisted store, where this PR now looks like one where three bots simply had nothing to say.

## Evidence

- decision.log `29696e` — `proves=participation_only`, `coderabbit remains unproven (refused_awaitable)`
- decision.log `309777` (WARNING) — operator merged over the accepted gap, naming "pr-agent and sourcery both participated_but_empty and CodeRabbit rate-limited and absent from this HEAD"
- `review-retrospective.md` § Recommendation — the gap, stated by the consumer that hit it; verdict **Unmeasurable**, `reviewer_count: 1`
- `manage-findings list --type pr-comment` — 2 records, both `cuioss-oliver`, zero bot-authored
