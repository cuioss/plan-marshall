# Check: merge-window-accounting (cross-plan)

Accounts for the **#849 widened merge-mutex + FIFO admission-queue window** — the
fair-merge-ordering / parallelism enabler introduced when the merge mutex was
widened. The merge serializer fronts a `k=1` `O_EXCL` mutex with a main-anchored
FIFO admission queue so the longest-waiting plan merges next; a non-front plan
returns a structured `blocked` re-poll signal and waits its turn. This check
accounts for the **merge window** each plan actually paid — the cost the widened
mutex trades for fair ordering — rather than inferring merge health from generic
symptoms.

The deterministic computation lives in `scripts/audit.py`
(`cross_merge_window_accounting` / `emit_merge_window_accounting_block`); this
sub-document is the interpretation guide. It is a **cross-plan** check: it scans
the corpus-wide global `[LOCK]` lifecycle logs once and buckets by plan.

## Inputs the check reads

The merge-lock primitive appends a best-effort `[LOCK] (merge:{event}) {lock_id}`
lifecycle line to the **main-anchored global logs** (`.plan/local/logs/`) on every
acquire / release / blocked-wait / stale-reclaim, with a following indented
`waiting_count:` field (the post-mutation FIFO queue depth). The `{lock_id}` is the
plan_id, so the corpus lines bucket per plan. Events:

| Event | Meaning |
|-------|---------|
| `acquired` | The plan reached the FIFO front and won the `O_EXCL` mutex. |
| `released` | The plan released the mutex and dequeued. |
| `blocked` | The plan was a non-front waiter (or lost the create) — it waited behind the admission queue. |
| `reclaimed` | The plan re-created the lock after reclaiming a crashed holder's stale lock. |

The check scans `.plan/local/logs/*.log`, matches `[LOCK] (merge:*)` lines, and
reads the max `waiting_count` observed on the following indented lines.

## Computation and flags

Per plan_id the script accumulates the acquire / release / blocked / reclaim counts
and the **max observed `waiting_count`** (the deepest the FIFO queue got while this
plan was involved).

| Flag | Fires when | Reading |
|------|-----------|---------|
| `merge_contention` | The plan was ever `blocked` (it waited behind the FIFO front) OR its max `waiting_count > 1` (other plans were queued behind it). | The plan paid a merge window — it did not get an uncontended straight-through merge. This is the window the widened mutex trades for fairness, NOT necessarily waste. |

A row's `in_corpus` column marks whether the plan is in the current scan (a
`[LOCK]` line for a plan outside the scanned corpus is still counted in the corpus
totals but flagged `in_corpus: false`).

## Emitted columns

```
plans_with_merge_events: P
contended_plans: C
total_blocked: B
max_waiting_observed: W
rows[N]{plan_id,in_corpus,acquired,released,blocked,reclaimed,max_waiting,flags,severity}
```

| Column | Meaning |
|--------|---------|
| `plan_id` | The `lock_id` (= plan_id) the merge events were bucketed under. |
| `in_corpus` | `true` when the plan is in the current scan's corpus. |
| `acquired` / `released` / `blocked` / `reclaimed` | Per-event counts. |
| `max_waiting` | The deepest FIFO `waiting_count` observed for the plan. |
| `flags` | `merge_contention` when the plan waited behind the queue, else empty. |
| `severity` | Uniform D1 severity column: `genuine` when `merge_contention` fired, else `informational`. |

## How the orchestrator interprets the rows

- **`merge_contention` (`severity: genuine`)** — the plan waited in the merge
  admission queue. This is **accounting, not a defect**: the widened mutex + FIFO
  queue exist to give merge contention a FAIR ordering (the longest-waiting plan
  merges next), which is the price of the parallelism the widening enables. Read a
  contended plan as evidence the fair-ordering machinery was exercised, not as a
  per-plan fault. A plan queued behind the mutex whose HEAD advanced (a rebase /
  re-review while it waited) legitimately re-runs CI — see the
  `merge_window_ci_rerun` coupling.
- **high `max_waiting` across many plans** — a deep, frequently-contended queue is a
  throughput signal: the corpus is merging under sustained contention. Surface it as
  a parallelism / merge-cadence observation, not a per-plan lesson.
- **`reclaimed > 0`** — a crashed holder's stale lock was reclaimed. A recurring
  reclaim signature is worth a lesson (a merge holder is crashing mid-merge); a
  one-off reclaim is expected crash-recovery.
- **no merge events for a plan** — the plan is absent from the rows (it merged
  without ever touching the lock, or its logs were dormated). Absence is "no
  recorded merge window", not "merged instantly".

The `cross-check-synthesis` coupling `merge_window_ci_rerun` joins
`merge_contention` with sequence `ci_rerun` / token-economics `finalize_heavy` —
see [`cross-check-synthesis.md`](cross-check-synthesis.md). Its caveat is
load-bearing: the coupling is accounting, not a waste verdict.

Per the SKILL.md Step-3 contract, EVERY emitted row is adjudicated with a stated
verdict and cited evidence; a row may be dismissed as informational/expected ONLY
with a cited reason (e.g. "single blocked-wait — the FIFO queue working as
designed").

## Critical rules

- The script is the single source of truth for the `[LOCK]` parse and the
  per-plan accumulation. Do not re-grep the global logs in chat.
- The `[LOCK]` line grammar (`_LOCK_MERGE_RE`) and the `waiting_count` look-ahead
  (`_LOCK_WAITING_RE`) are module constants mirroring the merge-lock primitive's
  `log_lock_event` format. If that format changes, edit `scripts/audit.py` rather
  than substituting a different reading.
- The `[LOCK]` lines live in the MAIN-ANCHORED global logs, so this check reads the
  same corpus as `global-log-analysis`; it is cross-plan by construction (one scan,
  bucketed by plan_id).
- This check is read-only; it never edits `.plan/` files.
