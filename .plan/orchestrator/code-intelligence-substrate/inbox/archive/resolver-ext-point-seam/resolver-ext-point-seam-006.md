envelope_version=1
sender_type=plan
sender_id=resolver-ext-point-seam
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T15:18:40Z

component=plan-marshall:workflow-integration-github
category=bug
title=A diff-size-cap review refusal classified as hard_quota tells every consumer to wait for a window that never opens

# A diff-size-cap review refusal classified as hard_quota tells every consumer to wait for a window that never opens

Found by `plan-retrospective` on PR #1067. Not remediated.

## What happened

Sourcery declined to review PR #1067. Two records of the same event disagree about why:

| Source | Recorded cause |
|---|---|
| `review-retrospective.md` | `refused_hard` (`hard_quota`, rate-limited) |
| inbox message `resolver-ext-point-seam-004` | `refused_hard` / `hard_quota` |
| `logs/decision.log` 12:37:07 (branch-cleanup) | "sourcery refused on a **150000-diff-character size limit, not a quota**" |
| `logs/decision.log` 14:30:36 (branch-cleanup, post-loop-back) | "sourcery **still** refuses on the 150000-diff-character size cap" |

The two decision-log entries are the agent's direct reading of the refusal. The
`hard_quota` label is what the `bot_completion` classification path emitted, and it is what
propagated into both persisted artifacts.

## Why the distinction is load-bearing, not pedantic

The two causes have **opposite remediations**:

- A **quota / rate-window** refusal is self-clearing. The correct response is to wait — and
  `review_rate_window_await` exists precisely to do that. CodeRabbit's refusal on this same
  PR was genuinely of this kind, and waiting would in fact have worked (it eventually did
  review, at 13:40, once a rebase re-triggered it).
- A **diff-size-cap** refusal is not self-clearing at all. Waiting is guaranteed to fail
  for as long as the diff exceeds the cap. The only remediations are to split the PR or to
  accept the gap knowingly.

Collapsing the second into the first produces advice that is confidently wrong: inbox
message 004's own suggested disposition reads "coderabbit's window will have reopened; a
late review on this PR should be read as a recurrence" — correct for CodeRabbit, and
inapplicable to Sourcery, whose 25-file / 150K-character diff will refuse identically
forever.

## Root cause

`hard_quota` appears to be functioning as a catch-all bucket for "refused and not
awaitable", conflating a **capacity** condition (transient, time-bounded) with a
**capability** condition (permanent for this input). The classifier is losing the one bit
that determines what to do next.

## Proposed action

1. Add a distinct refusal cause for an input-size / input-shape rejection —
   `refused_input_too_large` or equivalent — separate from `hard_quota`.
2. Make `review_rate_window_await` consult the cause: engaging an await against a size-cap
   refusal is a guaranteed-futile wait and should be refused at arm time, not discovered at
   timeout. This is the same failure shape as the two monitor watchers in this plan that
   timed out on tokens that could never match.
3. Carry the refusal cause verbatim into `review-retrospective.md` rather than
   re-narrating it, so the artifact cannot drift from the classifier.

## Generalizable rule

When an external service declines, the classifier must preserve **whether retrying the
same input can ever succeed**. Any taxonomy that merges "not now" with "not this input"
destroys the only bit the caller needs.

## Evidence

- `logs/decision.log:83` and `:90` — both branch-cleanup barrier entries naming the
  150000-character size cap explicitly and contrasting it with a quota.
- `review-retrospective.md` § Reviewer Participation — `refused_hard` (hard_quota,
  rate-limited).
- inbox message `resolver-ext-point-seam-004` § Observed table.
