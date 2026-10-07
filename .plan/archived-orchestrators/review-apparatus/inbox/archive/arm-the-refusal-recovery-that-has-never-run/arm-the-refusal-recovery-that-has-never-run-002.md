envelope_version=1
sender_type=plan
sender_id=arm-the-refusal-recovery-that-has-never-run
epic=review-apparatus
kind=candidate-lesson
created=2026-09-07T14:29:05Z

# Participation ledger re-stamps reviewed_commit_sha at fetch time

component: plan-marshall:workflow-integration-github
category: bug
confidence: high

## Context

`artifacts/pr-participation-currency-ledger.jsonl` is intended to answer "has bot B reviewed sha S?". It cannot, because `reviewed_commit_sha` records whatever HEAD was current when `fetch_findings` ran — not the sha the bot actually reviewed. The same unchanged comment is therefore re-recorded under every later head it happens to still be present at.

First-party evidence from this plan's own ledger (42 rows over 8 shas):

- `IC_kwDOQ3xasM8AAAABS4ng4A` appears under `937e23657` (twice) and again under `d75ded9ec`.
- `PRRC_kwDOQ3xasM7rTFi6` appears under `937e23657` and again under `1af159585`.
- `PRRC_kwDOQ3xasM7rVjc6` appears under `d75ded9ec` and again under `1af159585`.

## Root cause

The write path stamps the current head onto every row it files, so row presence at a sha proves only that the comment existed at fetch time — an *observation currency* fact — while every consumer reads it as a *review provenance* fact. The two are silently conflated, and the conflation is in the benign direction: a stale comment makes a sha look reviewed.

## Proposed action

Separate the two facts in the record: keep the observation head under a name that says so (e.g. `observed_at_sha`) and populate a review-provenance field only from the bot's own declared review target when the provider exposes it. Where the provider exposes no such field, record the absence explicitly rather than substituting the observation head — a consumer must be able to tell "reviewed at S" from "seen while S was HEAD" from "provenance unavailable". This is the substrate the merge gate needs before the sibling proposal (three-state fetch return) can be made reliable.

## Evidence

- artifact: `artifacts/pr-participation-currency-ledger.jsonl`, rows 15/17/25 and 19/28 and 26/29 — three comment ids each recorded under two or three distinct shas.
- aspect: llm_to_script_opportunities — proposes a three-state currency verb over this ledger as the highest-value scripting candidate of the run.
- related: this run's central defect (a merged sha reported as reviewed-and-clean) is the consumer-side symptom of this producer-side conflation.
