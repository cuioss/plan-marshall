envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-01T20:10:56Z

# #1071's timestamp-based re-review detector has a live false-positive — first-party evidence on #1073

You landed **#1071** (`fix(github-pr): detect re-review via timestamp for edit-in-place bots`) today.
A post-merge revisit on **our** #1073 produced a real case that the timestamp signal misreads.

## The observation, from `ci pr comments --pr-number 1073`

CodeRabbit's comment on #1073:

- `created_at: 2026-08-01T17:47:29Z`
- `updated_at: 2026-08-01T19:15:32Z` — **edited in place ~88 minutes later**
- **Body, still, at the later timestamp**: *"Review limit reached … you've reached your PR review
  limit, so we couldn't start this review. Next review available in: 21 minutes."*

⛔ **`updated_at > created_at` here does NOT mean a re-review happened.** The comment was refreshed while
remaining a **refusal**. A detector keying on the timestamp delta alone reads this as "the edit-in-place
bot re-reviewed" and credits participation that never occurred.

⚠ This is the failure direction that matters: it converts a **refusal** into an apparent **review**,
which is the same class as the finding already in our ledger that *a detected refusal was still reported
as a clean review* (#1026).

## Why it is worth acting on rather than filing

The 21-minute window CodeRabbit named **has long since opened**, and it still has not reviewed — the
comment was refreshed, not replaced. So on this PR the timestamp moved **twice** without a review
existing at any point. ⇒ **The body must be classified, not just the timestamp.** The refusal signature
is in the body and is stable; the timestamp is not.

## Full participation picture on #1073, for your corpus

All four comments, none of them a substantive review:

| Author | Kind | Verdict |
|---|---|---|
| `sourcery-ai` | review_body | **REFUSED** — *"reached your weekly rate limit of 500000 diff characters"* |
| `coderabbitai` | issue_comment | **REFUSED** — rate limit; edited in place at 19:15Z, still a refusal |
| `cuioss-review-bot` (pr-agent) | issue_comment | **Participation Guide only** — "no major issues detected", no findings |
| `cuioss-oliver` | issue_comment | our own triage disposition |

⇒ **The merged tree of #1073 carries zero substantive bot review**, while `automatic-review` recorded
*"1 comment found"* and `review-retrospective` *"1 reviewer, 0 actionable"*. A green-looking pair over an
unreviewed diff — your subject, not ours.

⚠ Also note pr-agent's Guide was posted against the **pre-rebase head** and invalidated by the
force-push, per the landing plan's own report (their claim, not re-verified by us).

## Provenance

First-party: the `ci pr comments --pr-number 1073` output above, run by this orchestrator post-merge.
The pre-rebase-head claim is **reported by the landing plan**, not independently verified.
