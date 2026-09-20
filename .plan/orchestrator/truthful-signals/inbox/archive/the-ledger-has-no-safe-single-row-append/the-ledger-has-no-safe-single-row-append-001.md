envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:17Z

component=plan-marshall:automatic-review
category=bug
confidence=high

# Post the registry-declared trigger token, never one chosen per bot

## Context

Re-review of PR #1424 stalled for over two hours because the wrong trigger token was posted. At 2026-09-06T09:40:15Z the run posted a comment whose body was `/review`. That is `cuioss-review-bot`'s declared `trigger_comment`. CodeRabbit declares `trigger_comment: "@coderabbitai review"`, declares `trigger_semantics: requires_explicit_trigger`, and has no push trigger — so it was never asked to review the new head at all.

The tell was available immediately: `cuioss-review-bot` answered that same comment 58 seconds later at 09:41:13Z while CodeRabbit produced nothing. The run instead read CodeRabbit's silence as a rate-limit window still being in force, and spent a 90-minute wait on it. The mistake was diagnosed at 11:49:43Z, and corrected at 11:51:14Z.

## Root cause

Which token to post for a given bot is declared registry data, but it was resolved by agent judgement at the call site. The registry already carries `trigger_comment` per bot; nothing read it. A silent bot was then attributed to a rate window rather than to never having been asked, because "no review appeared" is consistent with both.

## Proposed action

Add a verb that takes `--bot-kind` and posts the literal `trigger_comment` read from that bot's registry data block, so the token is never composed or chosen by an agent. Where a re-review trigger is fired, route it through that verb. Additionally: when a bot declaring `requires_explicit_trigger` is silent, check that a trigger carrying ITS declared token exists before attributing the silence to a rate window.

## Evidence

- decision.log 2026-09-06T11:49:43Z — "the trigger posted at 09:40:15Z (IC_kwDOQ3xasM8AAAABS05FEQ) has body '/review', which is cuioss-review-bot's trigger_comment, NOT coderabbit's '@coderabbitai review'. coderabbit declares trigger_semantics requires_explicit_trigger, so it never saw a trigger."
- decision.log 2026-09-06T11:51:14Z — "ORCHESTRATOR ERROR corrected ... Corroboration: cuioss-review-bot answered that comment 58s later at 09:41:13Z; CodeRabbit produced nothing."
- Elapsed cost: 09:40:15Z trigger to 11:49:43Z diagnosis = 2h09m, including one spent 90-minute wait.
