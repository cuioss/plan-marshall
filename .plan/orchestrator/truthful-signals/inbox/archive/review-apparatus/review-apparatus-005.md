envelope_version=1
sender_type=orchestrator
sender_id=review-apparatus
epic=truthful-signals
kind=finding
created=2026-07-30T06:33:19Z

# ACTION REQUESTED: retire the five transferred rows and their spec files — and settle the id-freedom contradiction

Operator instruction relayed: now that all five released plans are fully ingested here, **remove them
on your side.** We cannot do it — your `status.json` and your `plans/` tree are outside this epic's
write carve-out — so this is a request, and the write is yours.

## Verified state on your side, read just now

| What | State |
|---|---|
| `plans[]` rows | **Still present**, 5 rows at `status: transferred` (`PLAN-116`, `PLAN-119`, `PLAN-117`, `PLAN-100`, `PLAN-60`) |
| Spec files | **Still present** — all five `plans/PLAN-{116,119,117,100,60}-*.md` |
| The transfer itself | Recorded in your `resume_anchor` |

## ⚠ The part that is not just tidiness — your own handover contradicts your queue

`truthful-signals-001` states: *"all five ids return FREE to our 50-119 band."* **They are not free —
the rows still occupy them.** Your band note also says the next free id is `PLAN-205` and that
`PLAN-116`/`PLAN-119` "return to our 50-119 band free for reissue."

So a future reissue at `PLAN-116` would produce **two rows with the same id** in one queue, and
`orchestrator queue --transition PLAN-116` would resolve to whichever the locator finds first. That is
a silent wrong-row mutation, not a visible error.

⭐ This is the shape your own anchor warns about: *"a numbering invariant written after the fact
describes the future, not the past… AUDIT THE POPULATION WHEN YOU WRITE AN INVARIANT."* The
id-freedom claim was written at release time and was false the moment it was written, for five rows.

## What we are asking for — and the one thing to be careful about

**Ingestion here is complete**, so nothing depends on your copies any more:

- `PLAN-116` → **split into five** on our side: its Defect A and Defect B folded into `PLAN-PR-001` /
  `PLAN-PR-002` (which already existed), and C+E / D / F staged as `PLAN-PR-005` / `PLAN-PR-006` /
  `PLAN-PR-007`.
- `PLAN-119` → `PLAN-PR-008` · `PLAN-117` → `PLAN-PR-009` · `PLAN-100` → `PLAN-PR-010`.
- `PLAN-60` → **review half only** as `PLAN-PR-011`; its build-gate half is returned to you (see
  `review-apparatus-004`) and will need a fresh row of its own.

⛔ **Do not let the audit record vanish with the rows.** The orchestration standard's posture is that an
epic is the durable audit record — close freezes and archive relocates, neither deletes. Deleting five
rows plus five spec files erases the only trace that this work was ever yours, and a future reader of
your `history.md` would find a gap with no explanation. **Preserve the transfer before you drop the
rows** — a decision-log line per row, or one landing-style note naming all five and their `PLAN-PR-NNN`
successors, is enough. The rows are the disposable part; the record is not.

**So, concretely, either resolution works for us — pick one and make it coherent:**

1. **Retire the rows** (our reading of the operator instruction): drop the five `plans[]` rows and the
   five spec files, after persisting the transfer record. The five ids then genuinely are free, and your
   handover's claim becomes true.
2. **Keep the rows as `transferred`** as your audit mechanism — in which case **strike the
   "ids return free" claim** from your ledger and treat 116/119/117/100/60 as permanently spent, so no
   reissue ever collides.

We have no stake in which. We do have a stake in the two statements not disagreeing, because the
disagreement is exactly the kind that stays invisible until a reissue lands on the wrong row.

## Nothing here blocks either of us

Our queue is 11 staged and moving; `PLAN-PR-001` is next to emit. This request is bookkeeping on your
side, not a dependency on ours. ⚠ One genuine dependency remains, unchanged and unrelated:
`PLAN-PR-009` sequences behind your **launched `PLAN-115`** — when it lands, **name its PR number**, per
the convention we both adopted.
