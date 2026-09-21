envelope_version=1
sender_type=plan
sender_id=inventory-blind-spot
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-29T15:51:08Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall
source_plan=inventory-blind-spot

# `fetch_findings` reports a bot as `absent` after it has already been proven to have reviewed

## Observation — live on PR #1056, this run

`github_pr fetch_findings` does **not re-credit a review bot's already-proven participation** across
FIND calls. Participation is derived from the current call's comment scan, and a bot whose review
carries no fresh `updated_at` movement since the previous call reads as `absent` on the next one.

Concretely on PR #1056:

- pr-agent **genuinely reviewed at 15:07** — its `PR Reviewer Guide` comment is on the PR and was
  filed to the ledger as finding `7e3f74` (`bot_kind: pr-agent`, `reviewed_commit_sha:
  69f22701f2af543e5d10da10876d872d058b695a`, "No security concerns identified / No major issues
  detected").
- On **loop-back iteration 2**, the same bot read as **`absent`**.

Nothing about the bot's participation had changed. The signal moved because the *query* moved.

## Why this matters (confident-signal-hides-a-caveat)

`absent` and "reviewed clean" are the two outcomes the finalize gate branches on, and they demand
opposite actions: `absent` means wait / re-request / escalate, "reviewed clean" means proceed. A bot
that has already reviewed being reported as `absent` is a **confident signal with the caveat removed**
— the gate has no way to tell "I have not seen a review" from "I saw one and then forgot it."

This is the same family as the standing rule that `ci pr comments` is necessary but not sufficient
evidence of participation, and the #1026 observation that a *detected* refusal was still reported as a
clean review. Here the polarity is inverted: a *proven* review reported as no review. Both directions
of this signal have now been observed lying.

## Solution direction

Participation must be **monotonic within a plan's finalize run**: once a bot's review is observed and
filed to the findings ledger for a given `reviewed_commit_sha`, subsequent `fetch_findings` calls for
that same head SHA must report it as participating regardless of `updated_at` movement. The ledger
already carries everything needed (`bot_kind` + `reviewed_commit_sha` per finding) — the fix is to
derive participation from the ledger union with the current scan, not from the current scan alone.
Participation should reset only when the head SHA advances.

## Impact

Affects every orchestrated and non-orchestrated finalize that loops back. The visible symptom is a
finalize that waits on, re-requests, or escalates a review bot that already reviewed — and, in the
worst case, an operator merge-anyway decision taken against a false `absent`. On this run the operator
merge-anyway was taken for a genuinely rate-limited coderabbit, but pr-agent's spurious `absent`
sat alongside it in the same gate evaluation.
