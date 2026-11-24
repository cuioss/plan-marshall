envelope_version=1
sender_type=orchestrator
sender_id=client-framework-aspects
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:04:54Z

> Routed from epic `client-framework-aspects` (repository Token-Sheriff) by its orchestrator on 2026-11-24, at the operator's direction. Original message `plan-15-plan-12-residual-fixes-004.md`, sender plan `plan-15-plan-12-residual-fixes`, created 2026-11-24T11:11:26Z. The lessons store of that repository refuses bundle-prefixed `plan-marshall:*` components (`wrong_store`), so the lesson is handed to this repository, which owns the components.

# Candidate lesson: a full finalize review round costs about 0.5M tokens, so advisory-only findings should become documented follow-ups rather than trigger another round

**Source plan:** plan-15-plan-12-residual-fixes (PR #954)
**Signal:** signal_automated_review_count=1 (review-loop cost observed while remediating the bot findings)
**Suggested category:** improvement (finalize loop-back policy). This may be KNOWLEDGE rather than a defect lesson; the orchestrator should classify it.
**Suggested component:** plan-marshall:phase-6-finalize (loop-back and re-review policy)

## What happened

This documentation-only plan went through three full finalize review rounds:

1. The initial functional-review and code-review, which ended in a code-review `loop_back`.
2. Re-fires after commits b4b2a90d and cd6869fd. Inside this round, functional-review had to discard a verdict and restart because HEAD moved during the round (warning at 08:42:57Z).
3. A further re-fire after the bot-fix inline commit 74e1f9b3: functional-review, code-review, architecture-refresh, pre-push gate, push, ci-verify, automatic-review and sonar-roundtrip.

The operator estimates that each full round costs about 0.5M tokens. After round 3, the remaining review comments were advisory only: no correctness defect and no misleading statement. They were deliberately recorded as documented follow-ups (see inbox message `plan-15-plan-12-residual-fixes-001`) instead of being fixed, because a fix would have triggered round 4.

## Rule

**Do:** once a round leaves only advisory findings (style, optional extra detail, suggestions to extend a guard in code rather than in the docs), decline or defer them with a recorded reason and a follow-up artifact, then proceed to merge. Spend a further round only on findings that would leave the shipped text or code wrong.

**Don't:** fix every remaining advisory comment in place on a docs-only PR. Each fix commit moves HEAD, and every HEAD move re-fires the whole review band, at about 0.5M tokens per round.

**Related cost driver:** a commit made while a review round is running (the HEAD-moved-under-the-round restart in round 2) wastes the part of the round already spent. Make inline corrections between rounds, not during them.
