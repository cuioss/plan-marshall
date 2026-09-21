envelope_version=1
sender_type=plan
sender_id=a-failing-ci-call-reports-success
epic=review-apparatus
kind=candidate-lesson
created=2026-08-27T15:42:54Z

# The required review bot produced nothing while an optional bot produced every finding

component: plan-marshall:automatic-review
category: improvement
confidence: high
source_plan: a-failing-ci-call-reports-success
source_pr: 1356

## Context

The execution manifest configured `required_bots: pr-agent` and
`optional_bots: coderabbit,sourcery`. Observed behaviour on PR #1356 inverted that:

- **coderabbit** (optional) produced every actionable finding, then hit its
  1-review-per-hour quota and stopped.
- **pr-agent** (required) was `participated_but_empty` on every HEAD.
- **sourcery** (optional) refused structurally — its 150,000-diff-character size
  cap against a 4,493-line change, so it never reviewed at all.

`automatic-review` recorded `1 reviewed, 1 empty, 1 refused-structural` and the
step still closed `done`. Effective reviewer coverage was one bot deep, and that
bot was quota-limited.

## Root cause

The required/optional split encodes an expectation about which bot reviews, and
nothing reconciles it against which bot actually produced findings. A required bot
that participates but returns empty satisfies the participation gate while
contributing zero review coverage, so the gate's green is a statement about
participation rather than about review.

## Proposed action

Reconcile the configured required/optional split against measured productivity
across recent PRs and re-seat `required_bots` on the bot that actually reviews.
Separately, surface `refused-structural` distinctly from `empty` in the step's
display detail — a size-cap refusal is a permanent structural exclusion for large
PRs, not a transient miss, and this PR was 4,493 lines against a 150,000-char cap.

## Evidence

- status.metadata.phase_steps `automatic-review`: "0 comments; 1 reviewed, 1 empty, 1 refused-structural; triage pending", 4 firings
- execution manifest `automatic-review.required_bots: pr-agent`, `optional_bots: coderabbit,sourcery`, `bot_lists_provenance: answered`
- project:finalize-step-review-retrospective: "1 of 3 enabled reviewers measurable, 16 actionable comments"
