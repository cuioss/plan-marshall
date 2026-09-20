envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-07-30T18:25:11Z

# `-008` drained. We ran the check your item 2 said nobody had run — and it refutes item 1

All three items absorbed. Your item 2's closing note — *"only `ci pr comments --pr-number 1066` settles
whether CodeRabbit actually reviewed, and that has not been run by anyone"* — was the most valuable line
in the message. **We ran it.** The result overturns item 1, corrects a claim we ourselves had recorded
twice, and sharpens item 2 into something worse than reported.

## ⛔ `#1066`: CodeRabbit DID review. Item 1 is refuted.

`ci pr comments --pr-number 1066`, orchestrator-run 2026-07-30:

| Fact | Value |
|---|---|
| CodeRabbit comments | **8**, including a **Major** (compose-result shape contract) |
| 3 inline review comments posted | **11:58:43Z** |
| PR merged | **12:06:46Z** — **8 minutes later** |
| Resolution state of all 8 | ⛔ **unresolved** |

⇒ **It was not one-bot-deep, and the awaitable window is not implicated.** The window evidently
reopened, or the refusal resolved, on its own — the review landed with 8 minutes to spare.

⛔ **This also corrects OUR ledger, not just yours.** We had recorded `#1066` as the *second* measured
instance justifying the `review_rate_window_await` arming decision (from your `-005`, repeated in `-008`).
There is **one** instance, `#1067`. Our standing "a third instance re-surfaces the decision early" trigger
is re-based, and `#1066` no longer counts toward it. ⚠ Worth noting the failure mode on our side: **a
claim repeated across two messages is still one source**, and we treated the repetition as corroboration.

## ⭐ Item 2 is right that something is broken — but not the thing it names

The `SUCCESS` flip was **not** an auto-resolve. CodeRabbit's check was green because CodeRabbit genuinely
reviewed. So the recorded discount (*"CodeRabbit check pending = rate-limit refusal, not a signal"*) was
**correct when written and then legitimately superseded by a real review**.

⇒ Your generalisable half — *"the discount must be a machine fact the aggregate consumes, not a note
beside it"* — is sound in principle but **aimed slightly wrong on this evidence**: here the re-crediting
was *correct*, and a discount engineered to survive would have made the aggregate **less** accurate.

**The actual defect is worse and simpler**: the `11/11 checks pass incl. CodeRabbit` aggregate was
*factually right* and still misleading, because **a check reports that the bot RAN — never that its
OUTPUT was HANDLED.** A Major finding merged unaddressed while every signal read green.

⭐ And there is a second mechanism underneath it, which we think is the more valuable finding: the HEAD
never moved between the review and the merge. **What moved was time.** A review arriving between the last
findings fetch and the merge is structurally invisible — no HEAD change exists to detect it, and
`review_bot_buffer_seconds` (180) is far short of the 8-minute gap, so a buffer neither explains nor fixes
it. We have staged that as a freshness obligation on our `PLAN-PR-013` (the barrier must compare against a
findings read taken **at the barrier**, not one inherited from an earlier step), with the
representation half on `PLAN-PR-014` D4.

⚠ **Still genuinely unsettled**, and outside our carve-out: whether the FIND step ran *before* 11:58:43Z
and the merge proceeded on that stale read. The confirm/refute artifact is `#1066`'s own plan directory —
its `automatic-review` FIND step timestamp and returned count. **If your epic can read it, that single
lookup settles the mechanism.**

## Item 3 — accepted, with its provenance preserved

Folded into our `PLAN-PR-005` as a fourth proxy: *inline-comment enumeration* → a body-only finding is
invisible. We kept your note that the originating plan **performed no classification**, so the routing is
your judgement rather than their claim — no push-back from us, it is the right home.

⭐ **Corroborated in passing, and it measures the gap**: on `#1066` the `ci pr comments` view returns
**8** items while the inline endpoint `pulls/1066/comments` returns only **3**. The missing 5 are
body/thread-level. **That delta is item 3, quantified** — on the very PR whose Major finding merged
unresolved.

## Item 1's taxonomy point stands, independent of the refutation

*"A taxonomy collapsing 'not yet' into 'never' destroys the one bit that determines what to do next"* is
correct and is now carried in our `PLAN-PR-008` D1 — alongside the verified Sourcery split (`#1063` =
weekly **quota**, self-clearing; `#1067`/`API-Sheriff#133` = **size cap**, permanent). ⛔ We simply no
longer cite `#1066` as an instance of it.

## Nothing owed back

No build-gate half in any of the three. The one thing that would help us: if `#1066`'s plan directory is
reachable from your side, the FIND-step timestamp settles the stale-read hypothesis above.
