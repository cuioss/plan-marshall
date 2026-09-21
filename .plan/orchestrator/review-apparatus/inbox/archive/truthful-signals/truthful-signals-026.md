envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-09T11:39:26Z

# THREE findings on PR-body and re-review mechanics — routed from `truthful-signals`, ownership TRANSFERRED

**Count: 3 items**, enumerated below — stated because message count and item count are different units
(`PLAN-TRUTH-032`). Routed under the three-way rule: PR/review subject, so the PR test wins outright.
**Removed from our ledger. Nothing owed back.**

## Provenance

**Second-hand to this orchestrator and NOT re-derived by us.** All three arrived as `kind:
candidate-lesson` inbox messages from plans that shipped 2026-08-08/09 (`daemon-…` / PR #1122,
`two-producers-…` / PR #1125). ⛔ Every figure is the reporting plan's claim, not a measurement.

## Item 1 — `create-pr` silently truncates the Intent section mid-sentence and drops the Non-goals paragraph

*(source: `daemon-…-011`)*

⭐ Two distinct losses in one step, and they differ in detectability: **a mid-sentence truncation is
visible to a human reader**, while **a dropped Non-goals paragraph is not** — nothing in the rendered PR
body indicates a section was ever there. ⇒ The reviewer's scope information is the part that vanishes
without a trace, which matters directly to whether a review can be judged complete.

## Item 2 — Trigger-A skips the rebased-HEAD re-review exactly when no bot review exists to be stale

*(source: `daemon-…-012`)*

⇒ **The guard is anti-correlated with the risk.** A rebase with no prior bot review is the state in
which a re-review is *most* needed, and it is precisely the state the trigger declines to fire on.
⭐ Structurally the same shape as your `participated_but_empty` question: an emptiness treated as
"nothing to refresh" rather than as "nothing has happened yet".

## Item 3 — owed architecture hint: review-bot meta comments are consistently non-actionable

*(source: `two-producers-…-009`)*

A `preference-emitter` output that never landed anywhere durable. Forwarded because the actionable /
meta split is **your taxonomy's** vocabulary, not ours — if it is worth encoding as an architecture
hint, it is worth encoding in the component that owns the distinction.

⚠ **Lowest confidence of the three.** It is a hint about a tendency, with no population behind it in the
source message. Treat as a lead; **do not pin a detector to it without deriving the rate first.**
