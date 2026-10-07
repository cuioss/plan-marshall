envelope_version=1
sender_type=orchestrator
sender_id=deployment-and-refresh-gaps
epic=truthful-signals
kind=candidate-lesson
created=2026-09-02T20:14:35Z

> **Relayed from Token-Sheriff.** Source epic `deployment-and-refresh-gaps`, plan `outbound-hostname-verification-core` (PR #689), original message `outbound-hostname-verification-core-004.md`.
> Filed there as a candidate-lesson and refused by `manage-lessons add` with `wrong_store`: the component names a `plan-marshall` bundle that the Token-Sheriff store does not own. Content is unmodified below.

# Candidate lesson: pr-agent publishes by EDITING its existing comment in place, and the participation classifier reads that as `declined`

**Component:** `plan-marshall:automatic-review` (participation classifier / `review_completeness`)
**Category:** bug
**Evidence:** work log `94a58d` (16:40), decision log `5b3c55` (16:48), `f5278f` (18:59)
**Severity of the false negative: high — the documented remedy for `declined` is to ask the operator to merge unreviewed.**

## The mechanism

pr-agent (`cuioss-review-bot`) does **not** post a new comment per review. The PR comment
timeline carried exactly ONE `cuioss-review-bot` entry, created at 15:50:31, and nothing from it
afterwards. When re-triggered, it **edits that same comment in place**:

- `/review` trigger at 16:38:57
- "PR Agent Review" workflow run at 16:39:00 (`event=issue_comment`, completed)
- the existing comment's `updated_at` moves to 16:40:00
- its body now carries `(Review updated until commit faf76712c81ec0d459e50f1d164e62121f6c1c54)`
  followed by "PR contains tests", "No security concerns identified", "No major issues detected"

So the required bot **had** reviewed the current HEAD and cleared it.

## Why the classifier got it wrong

The classifier SHA-verifies only via the **`review` signal path**. The `issue_comment` signal
path does not inspect body content, so it never sees the embedded SHA. An in-place update
produces no new comment for the classifier to match, so it resolved
`head_sha_verified=false, matched_signal=issue_comment` -> **`declined`**.

The leaf then returned `escalate_ask{reason: re_review_timeout, outcome: declined,
declined_bots: pr-agent}`. Escalating on that verdict would have asked the operator to
**authorise merging UNREVIEWED** a TLS-relaxing change that both required bots had in fact
reviewed and cleared.

This is the dangerous direction of failure: the false negative manufactures pressure to bypass
review coverage that actually exists.

## Detection

Compare the comment's `updated_at` against its `created_at`. An `updated_at` later than
`created_at`, landing shortly after the review trigger, is an in-place republish. Then read the
body for the embedded reviewed-commit SHA — the `issue_comment` path currently does not.

## Fix shape

Teach the `issue_comment` signal path to do what the `review` path already does: scan the
comment body for an embedded reviewed-commit SHA, and treat an edited-in-place comment whose
body names the current HEAD as `participated AND current`. Until that lands, an
`escalate_ask ... declined_bots=pr-agent` verdict must be checked against the comment timeline
before it is put to the operator — this run refuted it on direct evidence and did not raise the
escalation.
