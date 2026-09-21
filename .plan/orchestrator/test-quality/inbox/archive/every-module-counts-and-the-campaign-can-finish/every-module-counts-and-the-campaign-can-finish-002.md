envelope_version=1
sender_type=plan
sender_id=every-module-counts-and-the-campaign-can-finish
epic=test-quality
kind=candidate-lesson
created=2026-09-04T16:25:08Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=every-module-counts-and-the-campaign-can-finish

# Recognise a size-cap refusal at FIND time instead of after the operator reads it

## Context

The plan shipped 515 files. Both size-capped review bots refused the diff — sourcery at its 300-file cap, coderabbit at its 100-file cap — and NEITHER refusal was recognised at FIND time. The refusal wordings were registered by hand mid-run in commit 394e0fcf. cuioss-review-bot triggered but never answered. No bot reviewed the diff on either tree, and the operator closed the gap with a merge authorization recording `reason: refusal_structural`, then had to re-grant it after a second rebase lapsed the first grant.

## Root cause

The bot registry matches refusal wordings by literal registration. A wording the registry has not seen reads as an ordinary (contentless) comment rather than as a structural refusal, so the review-completeness path does not classify the run as uncovered until a human reads the comment and says so. Two independent bots hit this in one run, which makes it a registry-coverage problem rather than a one-off wording drift.

## Proposed action

Two parts. First, treat an unmatched comment from a registered size-capped bot as a REFUSAL CANDIDATE rather than as ordinary content — surface it for classification instead of letting it pass silently. Second, make the registration path a script verb that appends an observed wording to the bot's standards file, so registering a new refusal shape is a recorded call rather than a hand edit landing in the plan's own diff.

## Evidence

- status.metadata.merge_authorizations.barrier-ask-override — `refused_structural=sourcery cap=300 files; refused_structural=coderabbit cap=100 files; measured_diff_size=515 files; cuioss-review-bot triggered, no answer`
- status.metadata.phase_steps.6-finalize.automatic-review — prior_firings [loop_back -> 6-finalize], firing_count 2, final display_detail `coverage gap accepted - 2 bots refused on diff size`
- commit 394e0fcf touched automatic-review/standards/coderabbit.md and sourcery.md mid-finalize
- aspect: chat_history_analysis — the loop_back is the only recorded loop-back on the plan
