envelope_version=1
sender_type=plan
sender_id=test-suite-anti-vacuity
epic=review-apparatus
kind=finding
created=2026-09-07T21:17:02Z

# Bot participation states are emitted but never persisted

Surfaced by `finalize-step-review-retrospective` (order 990) on plan
`test-suite-anti-vacuity`, PR #1443.

## The gap

`review_completeness` emits `bot_states` during `automatic-review` —
`participated` / `participated_but_empty` / `participated_stale` /
`refused_structural` / `absent`. **Nothing persists them.**

A step ordered after the merge can only read the `pr-comment` findings store,
which by construction holds records for reviewers that **produced findings**.
So a reviewer that participated and found nothing, a reviewer that refused
outright, and a reviewer that was never asked are all indistinguishable to any
post-merge consumer.

## Why it mattered concretely

On this plan the three required/optional reviewers behaved very differently, and
only one was measurable:

- **coderabbit** — 25 actionable findings across 5 review rounds, 19 fixed, 72%
  resolved-as-fixed, zero rejected. Fully measurable.
- **cuioss-review-bot** — participated repeatedly, **every artifact empty**
  ("No major issues detected", "No code suggestions found") on the same diff
  where CodeRabbit found 25 items.
- **sourcery** — `refused_structural` on every pass: 7,848 changed lines against
  a stated 150,000-diff-character cap. Reviewed nothing at any point.

That asymmetry is the most useful thing the review history had to say. The
retrospective **correctly refused to record it as a measurement** — the workflow
forbids scoring, ranking, or making an absence claim without an attributed
record — so it could only be written as a recommendation. The verdict existed at
`automatic-review` time and was thrown away before the step that needed it ran.

## Remedy shape

Persist the `review_completeness` `bot_states` verdict per HEAD into the plan
store at `automatic-review` time, so a post-merge consumer can distinguish
"participated and found nothing" from "never reviewed" — without inferring
either from an absence.

Plan-store hash: `1b0984`.
