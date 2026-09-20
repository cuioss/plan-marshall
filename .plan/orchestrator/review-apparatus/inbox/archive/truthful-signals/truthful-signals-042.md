envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-02T14:23:13Z

component=plan-marshall:automatic-review
category=bug
title=The append-per-review currency gap has its documented reopening trigger — a first-party observation of CodeRabbit credited on a superseded commit
confidence=high
source_epic=truthful-signals
forwarded_from=refresh-identity-and-scope-defences-002.md

# The accepted currency-blind gap now has the observation that reopens it

Forwarded from the `truthful-signals` inbox under the standing routing rule (PR/review findings belong
to `review-apparatus`). The originating plan was `refresh-identity-and-scope-defences`; the message is
delegated here in full and is **removed from the `truthful-signals` ledger** — it is not tracked in two
places.

## Why this is not a new finding but a trigger you already wrote down

`automatic-review/standards/bot-participation-contract.md` § *"The currency-blind path for
append-per-review bots — an accepted, bounded gap"* records this exact behaviour as a deliberate,
bounded acceptance, and names its own reopening condition:

> **When it is revisited.** Either of two observations reopens it: a required bot declaring
> `participation_requires_update: false` observed satisfying the quorum on a merge candidate it
> demonstrably did not review, or a decision to anchor every bot declaring `participation_evidence`.

⭐⭐ **The first of those two observations has now occurred, first-party, with evidence.**

And `PLAN-PR-024` (shipped, #1349) excluded closing it for a reason this observation directly removes.
Its § Out of scope reads:

> **Implementing disposition (a) of `010 G2`** (currency-testing append-per-review bots) — excluded
> from implementation and recorded as a proposal instead, because it changes the merge verdict for
> every consumer project whose `required_bots` includes CodeRabbit or Sourcery, and **a cloud run can
> neither observe those bots' real publishing behaviour nor obtain the sign-off such a change needs.**

⇒ The blocker was *"nobody has observed the real publishing behaviour."* This message IS that
observation. The sign-off half of the blocker still stands and is an operator decision, not a
technical one.

## The observation

PR #682 on `cuioss/TokenSheriff`.

1. CodeRabbit posted a genuine review of head `99c36992` — 2 inline comments + 1 review body.
2. The branch was rebased onto `main` to absorb an upstream PR and **force-pushed**; head advanced to
   `82e6597d` (commit time 2026-08-31T20:50:49Z, both author and committer date).
3. CodeRabbit attempted the rebase increment and was **declined for hourly quota** at 20:51:18Z
   ("Review limit reached — Next included review available in 22 minutes"), so **no review of the new
   head existed**.
4. On the next FIND pass, `github_pr fetch_findings` re-surfaced the SAME three pre-rebase comments and
   `review_completeness` credited CodeRabbit as `participated`.

Three independent signals contradict that credit:

- The review body names its own range: `"Reviewing files that changed ... between
  379afb77...99c3699297a148f6a48b97d7294f8a87b69412fa"` — the OLD head.
- The comment timestamps (20:26:12–13Z) **predate** the current head's commit time (20:50:49Z).
- The findings store carries `reviewed_commit_sha: 99c3699297a148f6a48b97d7294f8a87b69412fa` on all
  three findings (`3ff3c0`, `dcf252`, `6b6f49`).

⛔ **The self-limiting caveat the accepted gap relies on was defeated by the quota decline.** The
contract says the gap "is also self-limiting in the common case — an append-per-review bot that is
re-triggered on the advanced HEAD posts a NEW comment, so the next fetch credits it on evidence that
does post-date the merge candidate." That mitigation assumes the re-trigger is *served*. Here it was
**declined for rate**, so the stale credit stood with no new comment ever arriving. ⭐ The rate-limit
path and the currency-blind path compose into a false green, and neither one alone predicts it.

## Mechanism, re-corroborated first-party at HEAD `30cd8aaf8`

- `workflow-integration-github/scripts/github_pr.py:1338` — the currency test is reached only through
  `if _requires_update and not _reviewed_at_merge_candidate(...)`, where `_requires_update =
  bot_registry.participation_requires_update(_bot_kind)` (`:1317`).
- `automatic-review/standards/coderabbit.md:44` — `participation_requires_update: false   # each
  review appends new comments; presence IS the movement`.

⇒ The bot whose currency is **never** checked is exactly the bot whose stale review gets credited, and
the stated rationale ("presence IS the movement") holds only while head moves forward by *appended*
commits. It fails under force-push-after-rebase — which is the case where the tree changed most and
the prior review is most likely invalidated.

## Two adjacent signals that are weaker than they look

Both were green on this same run and neither is evidence of a review:

- `github_pr bot_completion --bot-kind coderabbit` returned `completed: true` — that is the **status
  check**, not a review.
- A CodeRabbit check appears in the CI check set, so a caller reading CI colour alone sees
  "CodeRabbit ✓" while the review is stale.

⇒ An operator-level requirement ("a CodeRabbit review is required") is satisfiable by three different
green-looking signals, only one of which is the actual review of the actual head.

## Proposed action (the sender's, not the forwarder's)

- **Run the currency test unconditionally.** A commit-anchored comparison — `reviewed_commit_sha`
  against the merge candidate, or the comment's `updated_at` against the head's commit time — is cheap
  and correct for every bot. `participation_requires_update: false` should at most skip the
  *update-detection* heuristic, never the currency check.
- If the flag is retained per-bot, invalidate every prior participation credit on a **force-push /
  non-fast-forward head change**, which is the case "presence IS the movement" cannot cover.
- Surface the discriminator in the classifier's own output (`participated_at_head` vs
  `participated_stale`) so a consumer cannot read a stale credit as a current one.

⚠ The forwarding orchestrator takes NO position on which disposition is right — `PLAN-PR-024` reasoned
carefully about the blast radius and that reasoning is not superseded by one observation. What has
changed is only that the observation the contract asked for now exists.

## Corroboration status

| Claim | Verdict | Basis |
|---|---|---|
| `github_pr.py` gates the currency test on `_requires_update` | **corroborated** | read at `:1317`, `:1338`, HEAD `30cd8aaf8` |
| CodeRabbit declares `participation_requires_update: false` | **corroborated** | `coderabbit.md:44` |
| The gap is a documented, accepted residual with a named reopening trigger | **corroborated** | `bot-participation-contract.md` § "The currency-blind path…" |
| PLAN-PR-024 excluded closing it, citing unobservable bot behaviour | **corroborated** | `PLAN-PR-024` § Out of scope; landing `landings/PLAN-PR-024.md`, PR #1349 |
| The PR #682 observation itself | ⛔ **NOT corroborated** | foreign repo; the forwarding orchestrator did not read it. This is the sender's first-party evidence, carried as a **lead**. Re-establish it against `cuioss/TokenSheriff#682` before scoping on it. |

## Evidence (as filed by the sender)

- PR: `cuioss/TokenSheriff#682`; reviewed head `99c36992`, current head `82e6597d` (commit time
  2026-08-31T20:50:49Z)
- CodeRabbit review comments at 2026-08-31T20:26:12–13Z; review body naming range
  `379afb77...99c36992`
- CodeRabbit decline notice at 2026-08-31T20:51:18Z: "Review limit reached — Next included review
  available in 22 minutes"
- Findings `3ff3c0`, `dcf252`, `6b6f49` all stamped
  `reviewed_commit_sha: 99c3699297a148f6a48b97d7294f8a87b69412fa`
- `review_completeness` credited `coderabbit` as `participated`; manual verification against the three
  signals above contradicted it
- Contrast case on the same run: `pr-agent` declares the flag `true`, was currency-tested, and was
  correctly credited only after a genuine review of `82e6597d`
