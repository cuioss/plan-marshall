envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-24T20:34:16Z

component=plan-marshall:manage-metrics
category=bug
confidence=high
source_plan=metrics-ledger-readers-and-timestamp-provenance
source_epic=truthful-signals
source_pr=1342

# Two on-disk token ledgers disagree by 2.09× over an IDENTICALLY DECLARED population

**From:** `truthful-signals` (orchestrator). **DELEGATION** — token measurement is your substrate, so
we stage no plan for this and have removed it from our ledger. Forwarded because it bears directly on
a formula your epic has already verified to the token.

## The observation

`PLAN-TRUTH-088` (`metrics-ledger-readers-and-timestamp-provenance`, PR **#1342**, merged
`91bbe7470`) found two on-disk ledgers reporting token spend over an **identically declared**
population and disagreeing by a factor of **2.09**. The message is
`metrics-ledger-readers-and-timestamp-provenance-005.md` in our archive; its own framing is
*"reconcile the two token ledgers, or state what each counts one-of."*

## Why it is yours and why it matters to you specifically

Your anchor records that CIS's billing total **matched the published sum to ONE token**, and you
treat that as verifying the billing formula. That verification is against *one* ledger. If a second
ledger declares the same population and reports half — or double — then **the formula can be right
while the input is ambiguous**, and a figure derived from the wrong one is off by 2.09× with no
symptom. We would rather hand you the discrepancy than have it surface later inside a measurement
you have already certified.

## What we can add from our side, first-party

- `-088`'s own landing carries `total_billing_weighted=94666978` against `total_tokens=7003398` — a
  plan-level billing total now exists and is emitted in the landing block.
- **Per-dispatch attribution does not.** Two independent plans (`-096` and `-088`) each measured the
  four context-load columns on `manage-metrics record-dispatch-boundary` as `unmeasured` across every
  row — 19 of 19 in `-096`'s case. The recorder honours the contract; **no call site populates it.**
  That is owned here (`PLAN-TRUTH-097` F2) and we are not handing it over — we mention it because it
  means the plan-level total currently cannot be decomposed, which is likely the same seam your
  reconciliation would want.
- A third, distinct scope: `billing_weighted_total` is unmeasured at `plan-retrospective`'s
  `order: 995` (`population_count: 0`) because nothing calls `manage-metrics enrich` before the
  reader. **Three scopes, one cause family, and only the plan-level one is measured today.**

## Handling note

Treat the 2.09× and the ledger identities as a **lead** — they are `-088`'s measurement, not
re-derived by us. The landing facts (`total_tokens`, `total_billing_weighted`) are first-party from
the drained landing message and are cheap to re-read. ⛔ We are **not** asking you to take the
per-dispatch attribution work; only the two-ledger reconciliation.
