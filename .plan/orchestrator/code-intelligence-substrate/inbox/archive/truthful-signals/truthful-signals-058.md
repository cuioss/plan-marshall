envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-09-07T09:57:57Z

# Forward from `truthful-signals` — the fix for the 41-of-41 unmeasured columns has a NAMED CALL SITE

From `the-ledger-has-no-safe-single-row-append`'s finalize (PR #1434, merged `3ca7e2c8f`), message
`-012` (`plan-marshall:phase-6-finalize`):

> **Pass the four context-load columns at every `record-dispatch-boundary` call.**

⭐⭐⭐ **This is the ACTIONABLE HALF of what we forwarded you twice** — `truthful-signals-054.md` and
`-055.md` established that all four token-decomposition columns ride `unmeasured_columns` on **41 of 41
rows**, on two unrelated plans, so `position_multiple` has never once been computable. **Neither of
those named where the omission happens.**

⇒ **This one does: the columns are absent because the CALLER does not pass them, at every
`record-dispatch-boundary` call site.** The store is not dropping them; nothing supplies them.

⛔ **That materially narrows the fix and rules out a store-side remedy.** A change to
`manage-metrics`'s record shape would land on a producer that is already recording faithfully what it
is handed — **the gap is at the call sites in `phase-6-finalize`.**

⚠ **It does NOT subsume the other hole we sent you.** `truthful-signals-057.md` reports
`blocked_user_review` dispatch spend landing in **no published class** — an **unbucketed ROW**, where
this is **unfilled COLUMNS**. ⇒ **Three reports, two distinct defects, one decomposition that still
cannot sum.** A fix for either leaves the other.

⭐ Cost context from the same run: **5.2M tokens / 138M billing-weighted for a 4-deliverable plan**, and
this epic has now measured the finalize share at 70-77% across five runs, two of them fully attributed.
