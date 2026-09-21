envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:05:29Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# classify_bot participation-precedence launders a live refusal into a pass

`classify_bot` checks **participation before refusal**, and the participation evidence it consults is **not HEAD-scoped**. A bot that reviewed an earlier commit and then refused the current one is therefore credited as `participated` — the live refusal is laundered away by stale evidence from a prior commit.

Observed live on plan `crashed-participation-gate-records-a-pass` (PR #1070) against **coderabbit**. It was harmless only because coderabbit is optional on this repo's required-bot set. Against a required bot the same path produces a green participation verdict for a review that never happened at HEAD.

This is PLAN-PR-013's wrong-commit class, surfacing in the classifier rather than in the fetch layer. It was deliberately NOT fixed in PR #1070 — the spec forbids consolidating PR-013 work into that plan.

## Solution

Two changes, both in `classify_bot`:

1. **Refusal precedence** — evaluate refusal BEFORE participation. A detected refusal at HEAD is terminal for that bot on that commit and cannot be overridden by any participation signal.
2. **HEAD-scope the participation evidence** — participation must be established against the commit under review, not against the PR as a whole. Evidence from an earlier commit is evidence about an earlier commit.

Add a regression test that constructs the exact live shape: bot reviewed commit A, refused commit B, HEAD is B. The expected verdict is `refused`, never `participated`.

## Impact

Every consumer that reads a per-bot participation verdict as "this bot reviewed the current diff" — the automatic-review gate, the loop-back clearance check, the finalize participation report. Under the current precedence, a stale review plus a fresh refusal reads as a clean review, which is the exact false-green shape the review-apparatus epic exists to eliminate.
