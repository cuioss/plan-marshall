envelope_version=1
sender_type=plan
sender_id=end-phase-replace-not-accumulate
epic=code-intelligence-substrate
kind=finding
created=2026-07-29T14:06:09Z

# Finding: re-entry damage across the archived-plan metrics corpus

Read-only damage assessment run as deliverable 3 of `end-phase-replace-not-accumulate`.
Nothing was repaired: every archived `metrics.toon` was opened read-only and is
byte-identical to its pre-assessment state. No report document was created.

## Three distinct counts (never conflated)

| Count | Value |
|-------|-------|
| **Archived plans examined** | **27** (27 archived plan directories, 27 carrying `work/metrics.toon` — coverage is complete, the two denominators agree) |
| **Plans affected by re-entry overwrite** | **2** |
| **Suspect phase rows** | **2** (one `5-execute` row per affected plan) |

25 of 27 examined plans show no loop-back re-entry at all. The damage is narrow
(2/27 plans), not corpus-wide.

## The two affected plans

| Plan | Re-entered phase | Recorded `total_tokens` | `dispatch_boundary_total` | Under-count |
|------|------------------|------------------------|---------------------------|-------------|
| `executor-version-split-resolvers` | `5-execute` | 61,810 | 789,783 | ~12.8x |
| `exploration-share-is-unmeasured` | `5-execute` | 278,562 | 1,185,704 | ~4.3x |

Both rows carry the exact replace signature: `total_tokens` sits far below the
append-only dispatch-boundary sum for the same phase, because only the final
close's delta survived the `=` assignment.

## Predicate used, and why it names a different phase than the warning

Pre-fix rows carry no `close_count`, so the re-entry had to be inferred from
timestamps. Both affected plans carry a top-level `boundary_monotonicity:
6-finalize` key — but `6-finalize` is **not** the re-entered phase. The detector
flags the phase whose recorded `start_time` precedes an earlier phase's
`end_time`, which on a `6-finalize -> 5-execute` loop-back is `6-finalize`
itself. The re-entered phase is recovered by inverse attribution: the
canonically-earlier phase whose `end_time` falls after the flagged phase's
`start_time`.

- `executor-version-split-resolvers`: `6-finalize.start = 2026-07-26T19:14:57Z`,
  `5-execute.end = 2026-07-27T05:37:59Z` -> `5-execute` was re-entered.
- `exploration-share-is-unmeasured`: `6-finalize.start = 2026-07-28T20:37:01Z`,
  `5-execute.end = 2026-07-29T06:37:44Z` -> `5-execute` was re-entered.

The independent token evidence above corroborates the timestamp inference on
both rows, so neither affected plan rests on the predicate alone.

## Per-field recoverability split (over the 2 suspect rows)

| Field | Verdict | Rows | Basis |
|-------|---------|------|-------|
| `total_tokens` | **recoverable** | 2 / 2 | `work/metrics-dispatch-boundaries-5-execute.toon` is append-only, so its summed `total_tokens` column stayed cumulative across re-entries. `cmd_generate`'s same-population `max(total_tokens, dispatch_boundary_total)` reconciliation already renders the recovered figure, so the *rendered* report is self-healed even though the raw field remains wrong. |
| `agent_duration_ms` | **unrecoverable** | 2 / 2 | No append-only counterpart exists. The stored values (4,586,021 and 3,940,583) are the last close's clamped delta only. Compounded pre-fix by `_clamp_worked_to_wall` bounding against a `duration_seconds` recomputed from the re-entry's own `start_time`. |
| `tool_uses` | **unrecoverable** | 2 / 2 | No append-only counterpart. Stored 204 and 414 respectively. |
| `retrospective_tokens` | **not at risk** | 0 / 2 | The field is absent from both `5-execute` rows — the retrospective only dispatches under `6-finalize`, which neither plan re-entered. Deliberately reported as a third category: "absent, so nothing was lost" is not the same claim as "unrecoverable". |

So: 1 field class recoverable (2 row-instances), 2 field classes unrecoverable
(4 row-instances), 1 field class never exposed on these rows.

## Secondary observations (not repaired)

1. `duration_seconds` on both suspect rows is the re-entry window's span, not the
   sum of every entry's active span, so the wall figure is also short. The fix
   accumulates it going forward; the archived values stay short.
2. `idle_duration_ms` was zeroed by the monotonicity guard on the **flagged**
   (`6-finalize`) row rather than on the genuinely re-entered `5-execute` row, so
   the guard protected the wrong row on both plans. This is the same inverse
   attribution as the warning itself and is worth noting as a live gap in the
   timestamp detector, independent of the write-side fix.

## Caveat on the affected count — it is a floor, not a certainty

The predicate is timestamp-derived by necessity (no `close_count` exists on
pre-fix rows). A loop-back that re-entered and re-closed a phase **before** the
later phase's recorded `start_time` would leave the boundaries monotonic and be
invisible to it. The affected-plan count of 2 is therefore a **lower bound** on
the true damage, not a proven ceiling. Plans closed after the accumulate fix
lands carry `close_count`, so the same question becomes exactly answerable for
them without inference.
