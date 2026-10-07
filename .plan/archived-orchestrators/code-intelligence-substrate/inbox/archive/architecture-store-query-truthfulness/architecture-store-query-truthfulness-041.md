envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:55:22Z

component=plan-marshall:automatic-review
category=improvement

# One PR, three reviewers, and only one of them measurable

Source: the `automatic-review` step's own outstanding state across three firings
(display_detail: "1 comment found - 1 reviewed, 1 empty, 1 refused-structural (triage
pending)"), corroborated by the review-retrospective step ("3 reviewers compared
(1 measured, 2 unmeasurable), 18 actionable comments").

Two observations from the run's review window.

1. Sourcery refused on SIZE: cause=size, cap=150000 diff characters,
   rate_limit_class=hard_quota. Because sourcery sits in optional_bots, the refusal is an
   ordinary settle and never an escalation — refusal recovery was explicitly NOT ARMED.
   That is the configured behaviour, but it means a large PR silently loses a reviewer
   with no signal beyond a log line.
2. Two of three reviewers produced nothing measurable — one empty, one refused — so the
   "3 reviewers compared" headline rests on a single measured participant.

## Solution

A review step's outcome should distinguish "N reviewers ran" from "N reviewers produced
comparable output". A refusal attributable to diff SIZE is also a plan-shape signal, not
just a bot-availability one: a PR spanning 78 files exceeded a reviewer's hard cap, and
that is actionable at decomposition time.

## Impact

CodeRabbit alone carried the review; its own review body reported "Included review
availability: 0 remain after this review".
