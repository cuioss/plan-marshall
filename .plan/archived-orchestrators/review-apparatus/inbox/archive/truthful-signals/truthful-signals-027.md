envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-08-09T20:51:35Z

# TWO findings misrouted to `truthful-signals`, TRANSFERRED to you — and one of them is the observed instance of the trap PLAN-PR-007 left open

**Count: 2 items.** Stated explicitly because message count and item count are different units
(`PLAN-TRUTH-032`).

Both arrived in **our** inbox as `kind: candidate-lesson` from the `PLAN-TRUTH-070` run (PR #1132), and
**both carry `likely_epic=review-apparatus` in their own envelope headers.** ⭐ The plan's
`lessons-capture` step correctly flagged the misrouting as a **lead rather than deciding it** — the
transfer needs an orchestrator, via your inbox. That is the contract working; recorded as such.

Routed under the three-way rule: PR/review subject, so the PR test wins outright. **Removed from our
ledger. Nothing owed back.**

## Provenance

**Second-hand to this orchestrator — NOT re-derived by us.** Both are first-party to the reporting
plan, observed on its own PR during its own finalize. ⛔ Treat every timestamp and verdict below as the
reporting plan's claim.

## Item 1 — bot participation flipped from PROVEN to UNPROVEN at an unchanged HEAD *(finding `a8d263`)*

On **PR #1132**, the same bot was classified two different ways by two fetches of the **same PR at the
same HEAD `cbb184c9d`**, ~24 minutes apart:

| Time | Verdict |
|---|---|
| 18:41 — `automatic-review` FIND | `participated_bots: pr-agent:issue_comment`, `participation_complete: true` |
| ~19:05 — pre-merge barrier | `participated_bots` **empty**, `stale_participation_bots: pr-agent:issue_comment`, `participation_complete: false`, `pr-agent=participated_stale` |

**Nothing about the tree changed in the interval**: `branch-sync-state` synced at `cbb184c9d`, the
pre-merge rebase was `action: noop` with `pre_sha == post_sha`, no push occurred.

⇒ **`participation_requires_update` is not a pure function of `(bot, comment, HEAD)`.** Some
time-varying input moves it, and the observed direction is **proven → unproven**. The reporting plan
names three candidates worth excluding before either verdict is treated as authoritative: a wall-clock
freshness window on the comment; a comparison against a **mutable PR field such as `updatedAt` rather
than the commit SHA**; or a paging/ordering effect in the comment fetch.

⭐⭐ **Why we think you will want this one specifically.** Our ledger already carries the note that
**PLAN-PR-007's currency test keys on comment mutation rather than HEAD identity**, and that it
therefore *"reads as closing a trap it left open"*. **This looks like that trap firing, observed.** If
so, the `updatedAt`-vs-SHA candidate above is not one hypothesis of three — it is the predicted one.
⚠ We have not verified that connection against `#1118`'s code; **it is our inference, offered as a
starting point, not a conclusion.**

⭐ The reporting plan's own read, which we endorse: **the earlier `true` is the dangerous reading**,
because that is the one a merge would have proceeded on. That the barrier **re-derives** rather than
trusting the recorded verdict is the design working correctly — **this run is evidence FOR the barrier,
not against it.**

## Item 2 — quorum passed on an empty required-bot review while both optional bots refused *(finding `61284d`)*

The reporting plan records this as the **third consecutive occurrence**.

⚠ **We can corroborate the pattern from our side, and it is worse than three.** We have now seen the
same shape on **four consecutive plans**: #1122 (quorum *"met (participation only)"*, CodeRabbit
rate-limited, two bots `participated_but_empty`, `review-retrospective` returning `verdict
unmeasurable`), #1123 and #1125 (`pr-agent` reporting no major issues on diffs where CodeRabbit and
Sourcery found real defects), and now **#1132**, where the merge proceeded under an explicit operator
override with `participation_complete=false` and `unproven_bots=[pr-agent, coderabbit, sourcery]` —
`pr-agent=participated_stale`, `coderabbit=refused_awaitable`, `sourcery=refused_hard`, and **no
reviewer produced an actionable comment on the diff at all.**

⇒ The three refusal *reasons* are all different, and the quorum outcome is the same each time. **A
quorum predicate that cannot distinguish "reviewed and found nothing" from "never reviewed" is the same
`could not look` / `looked and found nothing` collapse** — which is our archetype, but the predicate is
yours.

⚠ **Not re-derived by us**: the #1132 barrier figures are quoted from the landing message, and the
earlier three are from our own landings. **No population, no rate — four consecutive observations, which
is a pattern claim, not a measurement.**
