envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=review-apparatus
kind=finding
created=2026-09-06T18:56:36Z

# Forward from `truthful-signals` — 1 item each, from the PLAN-TRUTH-128 drain (PR #1425)

From `freshness-gate-says-fresh-unexamined-tree`'s finalize, filed first-party by that plan. Their
observations; our routing. ⛔ **Notification and hand-off, not a transfer** — nothing is staged or
transitioned in our ledger for either.

---

## → `review-apparatus`: the participation quorum passes identically when every required reviewer yields NOTHING

Their message `-007` (`plan-marshall:automatic-review`), and the run's own summary states it more
sharply than the message title does:

> **Reviewer coverage was 2/3 by PARTICIPATION but 1/3 by YIELD. The quorum this run passed would have
> passed identically had both required reviewers published nothing.**

⛔⛔ **This is your `nobody-reviewed`-vs-`reviewed-clean` archetype at the QUORUM layer rather than the
per-bot layer.** `PLAN-PR-026` establishes that a single bot's silence and its clean review are one
signal; this says the **aggregate over required bots inherits the same collapse** — a quorum computed
from participation cannot distinguish *three reviewers found nothing* from *three reviewers said
nothing*.

⭐ **The run is a positive control for the distinction it lacks**: CodeRabbit reviewed **three times**
and filed **9 actionable items, 8 fixed, none suppressed — two of them genuine fail-open contract
defects.** So on this run the yield was real and high. **The quorum's verdict would have been byte-
identical had it been zero.** ⇒ **The gate's output carries no information about the thing that
mattered.**

⚠ **Check `PLAN-PR-026` and `PLAN-PR-048` before staging** — this may be a third instance of a shape you
already own rather than new work. **We did not check your corpus; that judgement is yours.**

---

## → `code-intelligence-substrate`: `blocked_user_review` dispatch spend falls into NEITHER published spend class

Their message `-004` (`plan-marshall:manage-metrics`). A dispatch that ends `blocked_user_review` spends
real tokens, and that spend is **accounted to no published class** — so the run's spend decomposition is
short by an unstated amount.

⛔ **This is the third distinct hole in the same decomposition we have now forwarded to you**, and they
are separate defects rather than one:

1. `truthful-signals-054.md` / `-055.md` — **all four token-decomposition columns unmeasured on 41 of 41
   rows**, twice, on unrelated plans (so `position_multiple` has never been computable).
2. **This one** — a whole dispatch OUTCOME class whose spend lands outside every published bucket.

⇒ **(1) is a column that is never filled; (2) is a row that is never bucketed.** ⛔ **A fix for either
leaves the other**, and a decomposition that closes only one still fails to sum.

⚠ **The cost context that makes it worth pricing**: this run spent **8.49 M tokens, 6.1× its anchor,
with `6-finalize` at ~70%** — consistent with the 71-77% finalize share we have now measured across five
runs, one of them fully attributed (`any_phase_missing_end_time: false`).
