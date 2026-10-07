envelope_version=1
sender_type=plan
sender_id=one-coherent-automated-review-contract
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T21:05:19Z

component=plan-marshall:automatic-review
category=anti-pattern
bundle=plan-marshall

# A concluded check-run for a review bot means the check concluded, not that a review happened

## Observation

On PR #1041 (PLAN-92) CodeRabbit produced a `completed` check-run while posting only a
rate-limit refusal — zero review body, zero inline comments. Reading the check state would have
reported the required bot as "done". The only artefact that distinguished refusal from review
was the bot's actual published output.

This is the live confirming instance for the D6 deliverable that PLAN-92 shipped: participation
must be established from each bot's actual publish shape —

- **CodeRabbit**: a posted review body or inline comments.
- **PR-Agent**: the Guide `issue_comment`, tracked via presence plus `updated_at` movement —
  never inline-comment count, never check state.
- **Sourcery**: a posted review body.

Quorum over `required_bots` proves participation only; it never proves review quality.

## Do this instead

- Never read a check-run conclusion, a green finalize, or a `completed: true` state as evidence
  that a review bot reviewed. Those signals report that the bot's *integration* finished, which
  a refusal also satisfies.
- Establish participation from the bot's published output, per that bot's declared publish shape
  in the registry.
- A comment authored *by* a bot is likewise not a review *by* that bot — a rate-limit refusal is
  a comment from the bot that carries no review.

## Recurrence context

Directly on the epic theme (`truthful-signals`): a confident green state that hides the caveat
that nothing was actually reviewed. Reinforces the standing rule that only the bot's own
published output is evidence of participation; the shipped D6 detector is the machinery form of
that rule, and this run is a real-world case where the check state and the truth disagreed.
