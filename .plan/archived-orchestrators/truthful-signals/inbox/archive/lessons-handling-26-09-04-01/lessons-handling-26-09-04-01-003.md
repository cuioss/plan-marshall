envelope_version=1
sender_type=orchestrator
sender_id=lessons-handling-26-09-04-01
epic=truthful-signals
kind=candidate-lesson
created=2026-09-04T07:45:52Z

# Finding: a review bot's budget-exhaustion REFUSAL is classified as normal participation

> **Relayed from Token-Sheriff.** Source epic `lessons-handling-26-09-04-01`, original lesson `2026-09-03-23-001`, observed on PR #699. Body reproduced verbatim below the provenance line.

**Proposed component**: `plan-marshall:workflow-integration-github` (`github_pr fetch_findings`) and the `plan-marshall:automatic-review` participation contract
**Category**: `bug` — a refusal counted as an answer

⛔ **Why this is the sharpest instance of the collection's own theme**: the barrier's purpose is to establish that the configured bots actually reviewed. A refusal notice counted as participation makes the barrier report the one thing it exists to rule out — that a bot did NOT review — as satisfied. It fails toward less safety, silently.

---

# Sourcery budget-exhaustion refusal misclassified as normal participation

## Observation

On PR #699, `github_pr fetch_findings` classified a Sourcery comment as ordinary
participation (`sourcery:review_body`, and `refused_bots` empty) when the comment body was
in fact a rate-limit refusal notice: it stated the review budget of 250,000 diff characters
was exhausted and named a retry delay of 9 minutes.

The comment was therefore stored as a `pr-comment` finding as though it carried review
content, and the participation guard counted Sourcery as `participated`.

## Why it matters

A refusal and a review are opposite signals wearing the same shape. Counting a refusal as
participation asserts that a reviewer looked at the diff when it explicitly said it did not
— the same false-participation class the sibling `required_bots` defect produced from the
other direction, where a bot that HAD reviewed was reported absent.

The blast radius here was nil only because Sourcery sits in `optional_bots` on this project.
Had the same wording arrived from a bot in `required_bots`, the pre-merge barrier would have
counted an explicit "I did not review this" as satisfied coverage and allowed the merge.

## Directive

Extend the refusal recognizer to match Sourcery's budget-exhaustion wording so the comment
routes to `refused_bots` rather than to participation. The recognizer already has a refusal
path — the gap is pattern coverage for this specific phrasing, not a missing mechanism.

Worth checking at the same time whether the recognizer's patterns are keyed per bot or
shared: a per-bot pattern set will keep acquiring this gap once per vendor per wording
change, whereas a shared "declined / budget / quota / try again in N" family would cover
future phrasings from any bot.

## Evidence

- PR: cuioss/TokenSheriff#699
- Stored finding hash: `20066d` (filed as a `pr-comment` finding)
- `fetch_findings` reported `participated_bots: sourcery:review_body`, `refused_bots: []`
- Observed by the automatic-review FIND step during plan `plan-09-local-gate-truthfulness`
