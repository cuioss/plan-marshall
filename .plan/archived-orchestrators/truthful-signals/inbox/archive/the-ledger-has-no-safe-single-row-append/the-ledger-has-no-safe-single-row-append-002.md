envelope_version=1
sender_type=plan
sender_id=the-ledger-has-no-safe-single-row-append
epic=truthful-signals
kind=candidate-lesson
created=2026-09-07T08:07:18Z

component=plan-marshall:automatic-review
category=bug
confidence=high

# An acknowledgement is not a review - require a review object

## Context

CodeRabbit replied to the second trigger at approximately 14:33Z with "I will review the changes after 51ce4dd5c, including the fixes at 5dc5c390d". No review followed. By 14:44Z its persistent comment had been edited in place to "Review limit reached - Next included review available in 44 minutes". Across the whole run the markers counted 4 "I will review" acceptances against 5 "Action not completed" refusals, and no review object ever post-dated 07:38:52Z on that PR.

Crediting the acknowledgement as participation would have satisfied the pre-merge barrier's `participation_complete` predicate on a review that never happened, and the PR would have merged with one required reviewer never having seen the head.

## Root cause

An acknowledgement and a review are separate events on the same channel, and both are bot-authored movement on the PR. Any participation test keyed on "the bot produced new content addressed to this head" cannot tell them apart. Only the presence of a review object covering the head distinguishes them.

## Proposed action

State explicitly in the participation contract that a reply acknowledging a trigger is NOT a reviewed state, and keep the participation verdict keyed on a review object (or an equivalently positive completion signal) whose coverage includes the head. Where an acknowledgement is recognised at all, classify it as its own state - asked-and-acknowledged - which is neither participation nor refusal, and which must not satisfy the merge gate.

## Evidence

- decision.log 2026-09-06T14:44:48Z — "CodeRabbit ACCEPTED the second trigger at ~14:33Z ... but the review did NOT land ... AN ACCEPTANCE IS NOT A REVIEW - the acknowledgement and the actual review are separate events, and only the latter counts as participation. No review object post-dates 07:38:52Z."
- decision.log 2026-09-06T19:29:06Z — marker counts: "4 'I will review' acceptances vs 5 'Action not completed' refusals".
