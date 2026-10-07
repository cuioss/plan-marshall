envelope_version=1
sender_type=plan
sender_id=test-suite-anti-vacuity
epic=review-apparatus
kind=finding
created=2026-09-07T17:56:17Z

# CodeRabbit rate-window recovery: the trigger resets the window

Observed across PRs #1430 / #1442 / #1443 during plan
`test-suite-anti-vacuity`. This inverts the intuitive recovery strategy and is
not stated anywhere in the current contract.

## The observation

Every trigger fired while CodeRabbit's rate window was still closed **restarted
the window** rather than being ignored:

| Trigger | Time | New window advertised |
|---|---|---|
| force-push | 13:43:40Z | 50 minutes |
| close-and-reopen | 14:45:25Z | 52 minutes |
| force-push | 16:05:03Z | 40 minutes |

The 16:05:03Z refusal was an **in-place edit** of an existing comment,
re-stamped at the exact second of the push.

The recovery only succeeded once the sequence was: **wait for full expiry →
verify by READING (`pr reviews` / `pr comments`) → trigger exactly once**. That
produced a real review (run `1ba68f22`, `coveredCommitId` == HEAD).

## Why this needs stating explicitly

The skill's Branch 2 → 3 → 5 chain already encodes the right *ordering*. What
is missing is the statement that an early trigger **resets** rather than
no-ops. Without it, the natural implementation of "has the window cleared yet?"
is to trigger and see — which is precisely the action that guarantees it has
not.

## Two further facts established

- **The limit is account-scoped, not PR-scoped.** Close-and-reopen re-delivers
  the review request but recovers no quota. Branch 5 addresses *trigger
  semantics*; it is not a quota remedy, and the two are easy to conflate.
- **A fifth unparsed ETA phrasing**: `"Next included review available in 50
  minutes."` (also seen with 52 and 40). `refusal_pattern_drift[]` and
  `unrecognised_refusal[]` were empty each time, so refusal *detection* works —
  the gap is specifically `rate_limit_eta_patterns`. Consequence: the
  awaitable-window branch cannot size its own wait and falls back to a default
  instead of the stated duration.

## Also worth recording

The `CodeRabbit` CI check reported `SUCCESS` **ten times** on this branch while
the bot had published only refusals. Only reading the comment body — including
the `final_review_risk_coverage` marker's `coveredCommitId` — established what
had actually been reviewed.

Plan-store hash: `77b9fa` (window reset), `dda827` (ETA patterns), `a8a081`
(`wait-for-comments` blind to in-place edits).

# finalize-step-plugin-doctor can anchor to the plugin cache

Separate defect, same run. Step 4's executor regeneration **auto-detects** its
marketplace anchor, and on one observed run it selected the plugin cache
(`~/.claude/plugins/cache/plan-marshall`) rather than the worktree source.

A gate run from that state validates `manage-invocation-invalid` against
**pre-plan scripts** while reporting a pass for the worktree — the precise
false green the regeneration exists to prevent.

The failure is silent: both anchors regenerate successfully and both report a
script count. Only the `Using context:` line distinguishes them. Re-running
with an explicit `--marketplace-root .` produced
`auto-detected (marketplace/bundles)`, and only that run is trustworthy
evidence about the worktree.

Remedy shape: pin the anchor explicitly, or publish the resolved anchor so a
cache-anchored run is distinguishable from a worktree-anchored one.

Plan-store hash: `ae0969`.
