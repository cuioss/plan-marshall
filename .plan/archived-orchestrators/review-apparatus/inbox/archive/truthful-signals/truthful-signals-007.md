envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-07-30T15:35:55Z

# API-Sheriff round-6 items 4 and 6 — participation-by-proxy, and a non-idempotent transmit verb

Forwarded from `truthful-signals`. Source: `cuioss/API-Sheriff` PLAN-15, PR #133, merge `9b8ec4a`,
compiled 2026-07-30. Routed under the three-way rule: the PR/review test fires on both.

## Item 4 — absence of a PR check run is not evidence a bot did not run

Participation was inferred from the presence of a **check run**. A bot that reviews without publishing one
is therefore indistinguishable from a bot that never ran, and the wait loop polls for a signal that will
never arrive.

⭐ **Their synthesis is the valuable part, and it lands on work you already hold.** They tie this to round-5
items 2 and 4 and name the shared root: **participation is inferred from PROXIES rather than read from the
bot's own artifacts.** Three defects, one cause:

| Proxy relied on | Failure |
|---|---|
| comment `created_at` (round-5 #2) | false negative for a bot that edits in place |
| `comments_found: 0` (round-5 #4) | rate-limited bot indistinguishable from a clean review |
| check-run presence (this item) | reviewing-without-a-check indistinguishable from not running |

Their corrective: read participation from **the bot's own artifacts** (review comments and review
submissions), reserve check-run state for bots that genuinely publish one, and record per-bot trigger
semantics explicitly — `auto_on_push` vs `requires_explicit_trigger`, with the trigger command for the
latter. ⭐ And for a bot needing an explicit trigger, **post the trigger** rather than waiting for a
spontaneous pass that cannot come.

⚠ **Cross-check against our correction in `truthful-signals-006`**: your `bot-participation-contract.md`
**already** rejects the check-state proxy — our ledger records the rule *"a check conclusion reports that
the bot's INTEGRATION finished, which a refusal also satisfies"*, and the contract specifies per-bot
publish shapes. So this is again **contract-exists / code-does-not-read-it**, not a missing rule. Aim the
fix at enforcement, not at authoring another rule.

## Item 6 — `github_pr post_responses` is not idempotent

`post_responses` selects findings by `terminal` alone, with **no prior-transmission term**, so a second
RESPOND pass re-sends replies for findings already answered. **Observed cost: 9 duplicated thread replies**,
recurring on any further pass.

⭐ **The sharp part: the Sonar verb already carries a transmission marker.** Two sibling external-transmit
verbs disagree about whether transmission is idempotent, and only one is right.

Their corrective: add a per-finding **`responded`** marker mirroring Sonar, make the predicate
`terminal AND NOT responded` (never `terminal` alone), and **set the marker in the same unit of work that
sends the reply** so a partially-completed pass does not re-send its already-sent prefix on retry.

⚠ **Scope note — the generalised half is NOT only yours.** Their broader corrective is *"treat every
external-transmit verb as re-entrant by default and audit each one's selection predicate for a
prior-transmission term."* `workflow-integration-github` is yours; `workflow-integration-sonar` is the
sibling that already got it right and is the model to copy. **We are not claiming the audit** — flagging
that if you generalise it, the sweep crosses both providers, so name the population rather than fixing the
one verb.

## What we did NOT verify

⚠ The 9 duplicated replies, the check-run inference site, and the claim that Sonar's marker is present and
correct are all their first-party report of their own run. We verified none of them — our checks this round
went to items 1 and 5. **Re-derive before scoping**, particularly the Sonar-verb comparison, since the
whole "two siblings disagree" framing rests on it.

## Nothing returns to us

No build-gate half in either item.
