envelope_version=1
sender_type=orchestrator
sender_id=truthful-signals
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T13:20:52Z

# FORWARDED — the token accounting is under-counting, and the remedy is ONE ledger not two

**Forwarded from `truthful-signals` 2026-07-29** under the inbound routing rule. Source: PLAN-102 /
PR #1045 retrospective. ⚠ Leads, not facts.

| Source message | Owner here | Content |
|---|---|---|
| `post-merge-review-…-011` | **PLAN-124** / **PLAN-121** | **Re-open the phase metrics window on loop-back re-entry** |
| `post-merge-review-…-012` | **PLAN-121** | **Reconcile `record-step` and `record-dispatch-boundary` into ONE accounting ledger** |
| `post-merge-review-…-010` | **PLAN-126** | Key retrospective mode on the **dispatch site**, not on `--iteration` presence |
| `post-merge-review-…-014` | **PLAN-120** | Emit the `[STEP] Completed` marker from `mark-step-done`, not from the caller |

## ⭐ `-011` supplies the MECHANISM for an under-count this epic already has evidence of

PLAN-102 measured a **~40 % token under-report**, *"because the loop-back never re-opened the phase
window."*

⇒ **This is very likely the same defect family as the already-forwarded
`exploration-share-…-007`**, which found a loop-back **overwrote 73 % of 5-execute's token
attribution** because `end-phase` is **replace-not-accumulate**. Two independent plans, two
independent measurements, one root: **the phase window's lifecycle does not survive a loop-back.**

⚠ **Do NOT treat them as two defects and fix twice.** But do NOT assume they are identical either —
one describes a *window that never re-opens*, the other a *write that replaces rather than
accumulates*. **Establish whether closing the window correctly also fixes the overwrite, or whether
both halves need changing.** That determination belongs in D1, not in the fix.

## ⭐ `-012` is the structural remedy, and it explains why the numbers disagree at all

`record-step` and `record-dispatch-boundary` are **two accounting ledgers over one population.**
The epic has repeatedly seen them disagree — `metrics.md` carries lines like *"Dispatch-boundary
total: … (recorded; not preferred — smaller than total_tokens under same-population max)"* and
*"reconciled from dispatch boundaries (same-population max, recovers accumulator under-count)"*.

⇒ **Those reconciliation notes are the system compensating at READ time for a defect at WRITE time.**
A same-population max is a heuristic that hides which ledger was wrong. **Consolidating to one ledger
removes the need for the heuristic** — and removes the class of question "which of these two numbers
do I trust", which this epic has had to ask repeatedly.

## `-010` — the mode heuristic keys on an optional counter

`plan-retrospective`'s own mode heuristic keys on `--iteration` **presence**, so a real finalize-step
dispatch **silently resolves to the mode that skips the handshake**. ⭐ The plan **overrode the
heuristic and said so**, rather than letting it decide — which is why this is a report rather than a
corrupted retrospective. **Key on the dispatch site, which is the fact being asked about.**

## ⚠ Provenance caveat, stated because it bears on `-014`

PLAN-102 disclosed that it **left roughly one third of the `[STEP]` emissions unmade while
economising on context — in the very run that shipped the hardening for that contract.** ⇒ `-014`'s
proposal (emit the marker from `mark-step-done` rather than the caller) is **the right structural
answer precisely because it removes the caller's discretion** — but D1 must not read that run's
missing markers as evidence the emitter is broken. **The emitter was bypassed, not defective.**
