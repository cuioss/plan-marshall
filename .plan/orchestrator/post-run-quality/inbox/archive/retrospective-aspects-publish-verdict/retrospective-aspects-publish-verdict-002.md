envelope_version=1
sender_type=plan
sender_id=retrospective-aspects-publish-verdict
epic=post-run-quality
kind=candidate-lesson
created=2026-09-21T09:25:39Z

component=plan-marshall:plan-retrospective
category=improvement
confidence=high
title=Gate chat Tier 1 on the delivered/produced ratio, not only the upper budget bound

# Gate chat Tier 1 on the delivered/produced ratio, not only the upper budget bound

## Context

The chat-history two-tier gate selects Tier 1 when `no_signal == false AND
over_budget == false`. On this plan's own retrospective, both flags were false and the
contract therefore selected Tier 1 — over a payload of 69 delivered bytes out of
725,532 produced.

`over_budget` is correctly derived from `reduced_transcript_delivered_bytes` (the D3
fix did land here). But it only tests an UPPER bound: it asks "is the delivered text
too large to read", and can never fire on a payload that is too SMALL. A delivery
failure of any magnitude passes the gate as healthy.

## Root cause

The tier gate has one measurement of delivery and uses it for one direction only. The
contract itself already names the right signal one paragraph earlier — "the gap between
them is itself the signal when they do not [agree]" — but no gate consumes that gap.

## Proposed action

Add a delivery-integrity condition to the tier gate: when
`reduced_transcript_delivered_bytes` is materially below `reduced_bytes` (exact ratio to
be chosen; the observed failure was 0.01%), Tier 1 MUST NOT be selected.

This needs a third skip-reason token. The current contract declares a CLOSED set of two
(`transcript_too_large`, `transcript_unavailable`), and neither fits: the transcript was
found and read (4472 turns) and carried signal (123 operator turns), so it is not
`unavailable`; it is under budget, so it is not `too_large`. Propose
`transcript_undelivered`, and update every aggregation consumer per the contract's own
amendment rule.

## Evidence

- aspect: chat_history_analysis — `tier: 1` selected on `delivered_fraction: 0.0001`
- aspect: chat_history_analysis — finding: "the two-token skip contract has no token for this state"
- reference: `references/chat-history-analysis.md` Two-Tier Degradation Path and Skip-Reason Token Contract
