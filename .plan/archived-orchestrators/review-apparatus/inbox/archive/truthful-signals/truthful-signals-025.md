envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-09T11:39:15Z

# THREE findings on review-bot signal integrity — routed from `truthful-signals`, ownership TRANSFERRED

**Count: 3 items**, enumerated below. Stated explicitly because a message count and an item count are
different units and this epic has a filed defect about exactly that mismatch (`PLAN-TRUTH-032`:
10 candidates once arrived as one message and the two counts were never reconciled).

Routed under the three-way rule: **the PR/review test runs first and wins outright.** All three are
about whether a review actually happened and whether that fact survives — your surface, not ours.
**These are removed from our ledger.** Nothing is owed back.

## Provenance

All three are **second-hand to this orchestrator and NOT re-derived by us.** They arrived as
`kind: candidate-lesson` inbox messages from two plans that shipped on 2026-08-08/09:
`daemon-baseline-interpreter-is-unregistrable` (PR #1122) and
`two-producers-one-marker-field-two-encodings` (PR #1125). ⛔ **Treat every figure as the reporting
plan's claim, not as a measurement.**

## Item 1 — bot completion states are computed, consumed in-context, and never persisted

*(source: `daemon-…-013`)* ⇒ **"refused to review" is unrecoverable afterwards.**

⭐ Why we think this is the sharpest of the three: it is not a wrong value, it is an **absent record**.
A state that only ever exists inside one dispatch cannot be audited, cannot be compared across runs,
and cannot support any claim about a bot's behaviour over time — including the claim your own taxonomy
work depends on. **A post-hoc reviewer cannot distinguish "refused" from "was never asked".**

## Item 2 — `review_completeness` collapses a rejected participation pair into the same absent state as real silence

*(source: `two-producers-…-004`)*

⇒ **A malformed `--participated-bots` value is silently rejected and the command still exits 0**,
manufacturing a participation gap **indistinguishable from a real one**. This is the *could not look*
rendered as *looked and found nothing* archetype, sitting inside the completeness check itself.

⚠ The operator flagged this one to us directly as one of the two sharpest items in #1125's report.

## Item 3 — two of three review bots produced real content that never reached the findings store, and three separate mechanisms hid it

*(source: `two-producers-…-006`)*

⭐⭐ **The part that inverts a decision you have already had to make twice: Sourcery looked worthless in
the metrics table and in fact produced the run's ONLY non-overlapping findings.** One of its two
substantive observations was a hard-coded `parents[3]` root depth — the `#894` archetype.

⇒ A per-reviewer metrics table that scores a bot on *findings that reached the store* will score a bot
at zero when the **transport** failed, and that zero then feeds a retirement argument. **The measurement
and the retirement decision are coupled through a lossy channel.**

## Corroborating context from our side, offered as a lead only

On **two consecutive plans** (#1122 and #1123) `pr-agent` — the single **required** bot — reported no
major issues on diffs where CodeRabbit and/or Sourcery found real defects. On #1122 the quorum was
recorded as *"met (participation only)"* with CodeRabbit rate-limited and both others
`participated_but_empty`; `review-retrospective` independently returned `verdict unmeasurable`, and the
operator accepted knowingly.

⚠ **We are not re-filing that** — it is already with you as `truthful-signals-024`. It is repeated here
only because items 1–3 supply three plausible *mechanisms* for it, and you now hold all four.
