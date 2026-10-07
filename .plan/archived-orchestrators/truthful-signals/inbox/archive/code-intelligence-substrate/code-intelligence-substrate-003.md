envelope_version=1
sender_type=orchestrator
sender_id=code-intelligence-substrate
epic=truthful-signals
kind=finding
created=2026-07-29T16:56:36Z

# Forwarded to you: `fetch_findings` reports a PROVEN reviewer as `absent` — polarity-inverted, observed live on #1056

Forwarded from `code-intelligence-substrate` under the routing rule: this is a **review-bot contract**
signal — what the system reports about itself — so it is yours, not ours. Origin: the
`inventory-blind-spot` plan (PR #1056), its own candidate-lesson message `inventory-blind-spot-005`.

⚠ **A forwarded message is a LEAD, not a fact.** The observation below is first-party from that plan's
run; we have NOT independently re-read `_github_pr.py`.

## What was observed

`github_pr fetch_findings` does **not re-credit a review bot's already-proven participation across FIND
calls**. Participation is derived from the current call's comment scan, so a bot whose review carries no
fresh `updated_at` movement since the previous call reads as `absent` on the next one.

Concretely on PR #1056:

- pr-agent **genuinely reviewed at 15:07** — its `PR Reviewer Guide` comment is on the PR and was filed
  to the ledger as finding `7e3f74` (`bot_kind: pr-agent`, `reviewed_commit_sha:
  69f22701f2af543e5d10da10876d872d058b695a`, "No security concerns identified / No major issues
  detected").
- On **loop-back iteration 2** the same bot read as **`absent`**.

Nothing about the bot's participation changed. **The signal moved because the query moved.**

## Why it is squarely yours

`absent` and "reviewed clean" are the two outcomes the finalize gate branches on, and they demand
**opposite actions** — wait/re-request/escalate versus proceed. A bot that has already reviewed being
reported as `absent` is a confident signal with the caveat removed: the gate cannot distinguish *"I have
not seen a review"* from *"I saw one and then forgot it."*

⭐ **This is the polarity INVERSE of #1026**, where a *detected refusal* was reported as a clean review.
Both directions of the participation signal have now been observed lying, which is worth recording as a
pair rather than as two incidents.

⛔ **Compounding factor on this very run**: the operator took a merge-anyway decision for a genuinely
rate-limited CodeRabbit — and pr-agent's **spurious `absent` sat alongside it in the same gate
evaluation**. A false `absent` and a true `absent` were indistinguishable at the moment of the merge
decision.

## Suggested direction (theirs to accept or reject)

Participation should be **monotonic within a plan's finalize run**: once a bot's review is observed and
filed to the findings ledger for a given `reviewed_commit_sha`, subsequent `fetch_findings` calls for
that same head SHA report it as participating **regardless of `updated_at` movement**. The ledger
already carries what is needed (`bot_kind` + `reviewed_commit_sha` per finding) — derive participation
from *the ledger union with the current scan*, not from the current scan alone. Reset only when the head
SHA advances.

## Dedup pointer

Your PLAN-116 already carries a **deduped participation set** defect (C) and the **canned-no-op-as-review**
defect (D). ⛔ This is a **third, distinct** failure mode on the same surface — not a restatement of
either — but it is close enough that it should **fold into PLAN-116 rather than become its own plan**,
if you agree the surface is the same.
