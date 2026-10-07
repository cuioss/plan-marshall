envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-22T07:47:14Z

# Forwarded per standing dispatcher rule: PR-diff-size gate, before finalize enters the review-bot wait region

Forwarded from `truthful-signals` (2026-09-22 drain). Per the 2026-07-30 operator instruction on this
epic's own ledger, truthful-signals is a dispatcher for the PR-review theme, not an owner — every finding
and landing concerning PR-related work routes to review-apparatus. We stage no plan for it.

## Source

Inbox lesson `2026-09-21-08-001`, relayed via `lessons-handling-26-09-22-01` from plan
`tracked-orchestrator-store-resolver` (2026-09-21). Original body (hand-authored, no `component=`/
`category=` header, so invisible to `manage-lessons` tooling until now):

> "Gate PR diff size before finalize enters the review-bot wait region": three finalize steps each
> measured a 4028-file diff privately and published nothing; no consumer between measurement and
> `create-pr` reads a footprint-size fact. 69.2% of the plan's script wall time was spent polling two bots
> structurally incapable of reviewing the diff. Proposed: publish `files_total`/`insertions_total`/
> source-vs-data split from `compute-footprint`, gate at push/create-pr against GitHub's 65536-char
> comment cap and Sourcery's 300-file fetch cap.

## Split — one owner per item

The gate/wait-region half is entirely yours (bot payload caps, PR-diff gating before the wait region).
The measurement/publish half — "three finalize steps each measured it privately and published nothing" —
is `code-intelligence-substrate`'s cell (footprint derivation and evidence emission); we are sending that
half to them separately rather than folding it here. Please attach your own disposition/outcome to this
item per this epic's dispatcher convention.
