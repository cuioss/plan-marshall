envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:49:51Z

component=plan-marshall:automatic-review
category=anti-pattern
bundle=plan-marshall

# A review bot's green CI check is not evidence that it reviewed

On PR #1340, CodeRabbit's CI check reported `SUCCESS` while CodeRabbit had
**declined to re-review the merge candidate** — its 1-review-per-hour budget was
already spent on an earlier head. The check conclusion and the review
participation were independent facts that happened to be readable from the same
PR at the same instant, and only one of them was true in the sense a reader
would take it.

A check conclusion reports that the bot's own pipeline ran to completion. It
does not report that the pipeline produced a review of THIS head. A bot that
short-circuits on a rate-limit still exits zero, so the check goes green on the
refusal path exactly as it does on the reviewed path. The two paths are
indistinguishable from the check alone.

Establishing participation required reading the provider's comments for the
head in question — the only surface that carries a per-head artifact the bot
actually authored.

## Solution

Never treat a review bot's check conclusion as a participation signal. Read the
provider comments (`ci pr comments`) and confirm a comment exists that is bound
to the current head. When no such artifact exists, the correct verdict is
"not reviewed", regardless of the check colour.

Stated generally: **when a gate's pass condition is "the process finished" but
the fact you need is "the process produced output", the gate is not evidence.**
Ask for the artifact, not for the exit status.

## Impact

Applies to every review bot with a rate limit or a skip path — which is all of
them. The failure mode is a merge candidate that reads as reviewed by N bots
while having been reviewed by fewer, and it is silent: nothing in the PR
surface contradicts the green check. May overlap with existing corpus guidance
on review-bot participation; the orchestrator holds the cross-plan view needed
to judge whether this is new or a recurrence.
