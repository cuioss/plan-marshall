envelope_version=1
sender_type=plan
sender_id=gates-do-not-refire-over-the-loop-back-diff
epic=truthful-signals
kind=candidate-lesson
created=2026-08-01T19:10:45Z

component=plan-marshall:phase-6-finalize
category=anti-pattern

# PR #1073 merged CI-green with NO bot having read the diff — operator chose PROCEED UNREVIEWED

## Observation

PLAN-TRUTH-001 landed as **PR #1073**, merged **CI-green**, with **zero** automated review coverage of the diff. Per-reviewer state at merge:

| Reviewer | State | Detail |
|----------|-------|--------|
| pr-agent | **participation only** | posted a Guide, not a review of the diff |
| coderabbit | **refused** | `awaitable_window` |
| sourcery | **refused** | `hard_quota` |

The operator was surfaced this state and explicitly chose **PROCEED UNREVIEWED**. Recording it here so the epic holds the fact, not to relitigate the decision.

## Why this belongs to `truthful-signals`

This is the canonical instance of the epic's theme, and it is *already* a known recurrence:

- **A comment from a bot is not a review by it.** pr-agent's Guide is participation output. The corpus already records that `ci pr comments` is **necessary but NOT sufficient** evidence — a comment *from* a bot ≠ a review *by* it. This run is a fresh confirmation.
- **Two distinct refusal modes, both invisible in the merge signal.** `awaitable_window` (the bot declined because its wait window elapsed) and `hard_quota` (the bot declined because it is out of budget) are *different* problems with different remedies, and neither surfaces as anything but "no review comments".
- **Green CI carried the merge.** The merge signal was truthful about CI and silent about review, and the composite reads as "PR passed".

## Standing obligation this triggers

Per the epic's standing rule, **every landed plan gets a post-merge PR revisit** — the merge routinely outruns the review (58 s on #1026, 2 m 42 s on #1036). Here the review never happened at all, so the revisit is not optional:

1. Re-check #1073 for late-arriving reviews.
2. **Scan sibling PRs** — a late or refused review is a *recurrence*, not an incident, and `hard_quota` in particular is account-wide, so contemporaneous PRs are likely affected too.

## Structural note

`hard_quota` and `awaitable_window` refusals are **account-level / time-window** conditions, not PR-level ones. That means they arrive in **bursts** across every PR merged in the same window. Any accounting of "which PRs were actually reviewed" must therefore be done over the window, not per PR.

## Not actioned

Operator decision recorded, not overridden. Handed to the epic for the post-merge revisit and the window-scoped sibling scan.
