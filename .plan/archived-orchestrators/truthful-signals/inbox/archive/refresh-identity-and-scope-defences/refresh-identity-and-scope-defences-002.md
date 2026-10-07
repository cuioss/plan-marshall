envelope_version=1
sender_type=plan
sender_id=refresh-identity-and-scope-defences
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T21:45:00Z

component=plan-marshall:automatic-review
category=bug
title=participation_requires_update=false credits a stale pre-rebase review as current participation, producing a false-green required-bot quorum
confidence=high
source_plan=refresh-identity-and-scope-defences

# `participation_requires_update: false` credits a stale pre-rebase review as current participation

A required-bot quorum reported a bot as `participated` on the strength of comments that reviewed a **superseded commit**. The gate exists to prove "a required reviewer has examined the tree about to merge"; on this run it would have certified that for a tree the reviewer never saw.

## What happened

PR #682 on `cuioss/TokenSheriff`. CodeRabbit posted a genuine review of head `99c36992` (2 inline + 1 review body). The branch was then rebased onto `main` to absorb an upstream PR and force-pushed, advancing head to `82e6597d`. CodeRabbit attempted the rebase increment and was **declined for hourly quota** ("Review limit reached — Next included review available in 22 minutes"), so no review of the new head existed.

On the next FIND pass, `github_pr fetch_findings` re-surfaced the SAME three pre-rebase comments, and `review_completeness` credited CodeRabbit as `participated`. Three independent signals contradict that credit:

- The review body names its own range: `"Reviewing files that changed ... between 379afb77...99c3699297a148f6a48b97d7294f8a87b69412fa"` — the old head.
- The comment timestamps (20:26:12–13Z) **predate** the current head's commit time (20:50:49Z, both author and committer date).
- The findings store still carries `reviewed_commit_sha: 99c3699297a148f6a48b97d7294f8a87b69412fa` on all three findings.

## Root cause

`github_pr.py`'s currency test `_reviewed_at_merge_candidate` is invoked **only** for bots whose registry declares `participation_requires_update: true`. CodeRabbit's registry (`automatic-review/standards/coderabbit.md`) declares it `false`, on the stated rationale that "each review appends new comments; presence IS the movement".

That rationale holds while head only moves forward by appended commits — a fresh review then really does mean fresh comments. It fails under **force-push after rebase**, which is the case that matters most: the tree changed the most, the prior review is the most likely to be invalidated, and the same comment objects are re-surfaced by the next fetch. The bot whose currency is *never* checked is exactly the bot whose stale review gets credited.

The declaration also encodes an assumption about a third party's posting behaviour that the pipeline cannot enforce and does not re-verify.

## Why this is a truthful-signals defect

The failure is not a missing check but a **check that reports the wrong thing while looking correct**. `participated` is the same token whether the review is current or two heads stale, so no consumer downstream can tell them apart — the verdict is not merely incomplete, it is confidently wrong. Its consumer is a merge gate, so the blast radius is a merge certified as reviewed by a reviewer that never saw the tree.

Two adjacent signals are also weaker than they look and should not be substituted for a review:

- `github_pr bot_completion --bot-kind coderabbit` returned `completed: true` on this same run. That is the **status check**, not a review; a green check is not evidence any review was posted.
- A CodeRabbit check also appears in the CI check set, so a caller reading CI colour alone sees "CodeRabbit ✓" while the review is stale.

An operator-level requirement ("a CodeRabbit review is required") is satisfiable by three different green-looking signals here, only one of which is the actual review of the actual head.

## Proposed action

- **Run the currency test unconditionally.** A commit-anchored comparison — `reviewed_commit_sha` against the merge candidate, or the comment's `updated_at` against the head's commit time — is cheap and correct for every bot. `participation_requires_update: false` should at most skip the *update-detection* heuristic, never the currency check.
- Treat the flag as an optimisation over how movement is detected, not as permission to skip whether the review describes the current tree.
- If the flag is retained per-bot, invalidate every prior participation credit on a **force-push / non-fast-forward head change**, which is the case the "presence IS the movement" assumption cannot cover.
- Consider surfacing the discriminator in the classifier's own output (`participated_at_head` vs `participated_stale`) so a consumer cannot read a stale credit as a current one — the same "make the zero say whether it looked" discipline this epic applies elsewhere.

## Evidence

- PR: `cuioss/TokenSheriff#682`; reviewed head `99c36992`, current head `82e6597d` (commit time 2026-08-31T20:50:49Z)
- CodeRabbit review comments at 2026-08-31T20:26:12–13Z, review body naming range `379afb77...99c36992`
- CodeRabbit decline notice at 2026-08-31T20:51:18Z: "Review limit reached — Next included review available in 22 minutes"
- Findings `3ff3c0`, `dcf252`, `6b6f49` all stamped `reviewed_commit_sha: 99c3699297a148f6a48b97d7294f8a87b69412fa`
- `review_completeness` credited `coderabbit` as `participated`; manual verification against the three signals above contradicted it
- Registry declaration: `automatic-review/standards/coderabbit.md` → `participation_requires_update: false`
- Currency test call site: `workflow-integration-github/scripts/github_pr.py` → `_reviewed_at_merge_candidate`
- Contrast case on the same run: `pr-agent` declares the flag `true`, was currency-tested, and was correctly credited only after a genuine review of `82e6597d`
