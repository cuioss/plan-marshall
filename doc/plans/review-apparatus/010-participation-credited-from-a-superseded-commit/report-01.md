# Run report — 010-participation-credited-from-a-superseded-commit (run 01)

**Date (UTC):** 2026-08-10    **Branch:** `claude/participation-superseded-commit-uo7k92` (harness-assigned, kept as-is)    **PR:** _pending_    **Outcome:** _in progress_

## Skills loaded

- `cloud-plan-lane` (the working contract; loaded first)
- `plan-marshall:ref-code-quality` (read from bundle path)
- `pm-plugin-development:plugin-script-architecture` (read from bundle path)
- `pm-dev-python:python-core` (Python production code)
- `pm-dev-python:pytest-testing` (Python tests)
- `plan-marshall:persona-implementer` (production-code work identity)

All obtained by the bundle-path route; none unreachable.

## Deliverables

### D0 — site population + anchor per site (GATE)

**Enumeration method (re-runnable).** `Grep` the participation symbols
(`_has_update_movement`, `participation_requires_update`, `reviewed_commit_sha`, `head_sha_verified`,
`participated_stale`/`stale_participation`, `participation_complete`) over `**/*.py` and `**/*.md`;
read the producer→consumer call graph from `github_pr.fetch_findings`'s return keys
(`participated_bots`, `stale_participation_bots`, `refused_bots`) to their consumer
`review_completeness.check_completeness` and its barrier caller in `branch-cleanup.md`; and
`github_re_review.await_fresh_review`'s `head_sha_verified` to its consumer `branch-cleanup-rereview.md`.
The registry (`bot_registry.participation_requires_update`) confirms **PR-Agent is today the sole bot**
subject to the S1 currency test.

**The site table — reported per site, never one global answer:**

| # | Site | Anchor (which commit the credit is compared against) | Idempotent? |
|---|------|------|------|
| S1 | `github_pr.py` `_has_update_movement` + participation loop — the currency test for `participation_requires_update` bots | **NONE.** Observation-history (`observed_keys`) for arm 1 (first presence) + `updated_at != created_at` for arm 2. No SHA is consulted on either arm. | **NO.** The first fetch *consumes* the first-presence arm; a second fetch of the same unedited comment **at the same HEAD** flips `participated`→`participated_stale`. The module's own comment states this design: "the record only ever closes that arm on a LATER fetch." |
| S2 | `github_pr.py` participation loop, non-`requires_update` bots (coderabbit, sourcery) | NONE — presence of a declared evidence kind; no currency test runs at all for these bots. | Idempotent (pure over the comment set), but currency-blind. |
| S3 | `github_re_review.py` `_match_review` (the re-review "obtain" review path) | **HEAD SHA.** `review.commit_sha == head_sha` → `head_sha_verified: true`. | **YES** — pure comparison of `commit_sha`/`submitted_at` against fixed inputs. |
| S4 | `github_re_review.py` `_match_bot_comment` (the re-review "obtain" comment path) | **NONE.** Timestamp vs `trigger_time`; a comment carries no reviewed SHA → `head_sha_verified: false`. | Idempotent (pure), but SHA-blind. |
| S5 | `review_completeness.py` `classify_bot`/`check_completeness` (the quorum consumer) | NONE directly — it trusts the producer's verdict sets. | Idempotent given fixed inputs (pure); but its inputs are produced by S1, which is not. |
| S6 | `branch-cleanup.md` Pre-Merge Review-Completeness Barrier (Predicate 2) | The **live HEAD** — re-runs `fetch_findings` (which re-stamps `reviewed_commit_sha` to the current HEAD) then `review_completeness`. Re-derives per fetch, not per stored record. | Inherits S1's non-idempotence — its `fetch_findings` call *is* S1. |
| S7 | `branch-cleanup-rereview.md` step 3 (trigger-A re-review consumer) — **the "recorded-but-ignored bit"** | Reads `matched` + `timed_out`, **ignores `head_sha_verified`**. A `head_sha_verified: false` comment-only match is credited as "the fresh review is now on the PR." | The read itself is idempotent, but it consumes S4's SHA-blind bit and **discards** the one bit (S3-vs-S4) that names whether the SHA was verified. |
| S8 | `_github_pr.py` / `github_ops.py` `pr wait-for-comments` predicate — the movement arm that is the **input** to S1's currency test | Timestamp/count movement; no SHA. | Idempotent (an await-completion timing signal, not a credit). The contract doc's "Recorded exclusions" already names it as "the *input* to the currency test rather than the classification it feeds." |

**The contradiction D0 surfaces (D1 must resolve):** **S3** demonstrably *withholds* credit unless the
reviewed SHA equals the merge candidate (SHA-anchored, `head_sha_verified: true`). **S1** demonstrably
*credits* participation with **no SHA consulted**, so a review of an earlier commit satisfies the gate
at a later commit — and it flips on the second look. Two sites, opposite answers, from what should be
one contract. And **S7** computes the deciding S3-vs-S4 bit and then throws it away.

**Data constraint discovered (shapes the D2 fix).** A fetched *comment*
(`github_ops.fetch_pr_comments_data`) carries **no reviewed-SHA** on any kind — only
`created_at`/`updated_at`. Only a *review* (`_github_pr.fetch_pr_reviews_with_commits`) carries
`commit_sha`. The per-finding `reviewed_commit_sha` (the PR HEAD stamped at ingestion) is therefore the
only durable per-comment SHA available to S1, and PR-Agent's contentless Guide is dropped as noise so
it has **no finding** — only a key in the noise-dropped sidecar. D2 therefore extends that sidecar to
carry the stamped SHA.

**Gate verdict: the site population was derived from the tree (grep + call-graph + registry); the plan
proceeds.**

### D1 — the stated rule
_in progress_

### D2 — re-key the currency test onto HEAD SHA
_in progress_

### D3 — `declined` state, excluded from quorum
_in progress_

### D4 — mutation-proven tests
_in progress_

## Build gate
_pending_

## Findings
_pending_

## Reviewer participation
_pending_

## Cost
_pending_

## Contract check (Step 9)
_pending_

## What have we learned (Step 9)
_pending_

## Residue
_pending_
