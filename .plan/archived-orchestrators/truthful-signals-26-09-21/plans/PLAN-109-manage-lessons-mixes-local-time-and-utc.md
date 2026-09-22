# PLAN-109: `manage-lessons.py` mixes local time and UTC — the id prefix and the retention math disagree on the date

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Staged 2026-07-28 from epic inbox finding `truthful-signals-004`.

## Objective

One file uses two clocks. The lesson-id prefix is derived from **local** time; the retention math,
the `removed_at` tombstone, and the `today` comparisons are derived from **UTC**. In a positive-offset
zone the two disagree for a window each night equal to the offset. Settle the file on one clock — or,
if the local choice was deliberate, label it — but do not leave them silently divergent.

## The divergence — OBSERVED

`marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/manage-lessons.py`:

- **Line 131** — `now = datetime.now().astimezone()` → **local time**. Feeds
  `date = now.strftime('%Y-%m-%d')` and `hour = now.strftime('%H')`, which compose the lesson-id
  prefix `{date}-{hour}` used for **sequence allocation**.
- **Lines 293, 411, 804, 1011, 1085** — `datetime.now(UTC)` → **UTC**. Feed the `removed_at`
  tombstone, the `today` values, and the retention / quiet cutoff comparisons.

⭐ **Line 131 is the outlier repo-wide.** Every other timestamp producer is UTC — `manage-status`,
`manage-metrics`, `jsonl_store`, `manage-ci-artifacts`, `plan-retrospective/compile-report.py`,
`generate_executor`, `_build_result`.

## The failure window

In a UTC+N zone, between `00:00` and `N:00` local, the local date has already rolled over while UTC
has not. On this machine (CEST, UTC+2) that is a **two-hour window each night, 00:00–02:00 local**,
during which a lesson filed gets id prefix `2026-07-29-00` while the retention cutoff, the
`removed_at` tombstone, and the `today` comparison all still resolve to `2026-07-28`.

**Consequences to check when actioning:** sequence allocation scans for existing ids sharing the
prefix, so a prefix computed on a different calendar day than the retention math can (a) collide
against, or (b) fail to see, the ids its UTC-keyed siblings reserved. Retention arithmetic keyed off a
date the id does not share also means an **off-by-one-day age** for lessons filed in that window.

⚠ **Stated honestly: the exact reachable symptom was NOT reproduced.** This is filed as an
inconsistency with a demonstrated divergence window, not as a reproduced failure. The plan must
establish reachability before claiming a bug — and **"not reachable" is a legitimate, valuable
outcome** that still leaves the consistency fix worth making.

⭐ **Zone-dependence is the load-bearing detail:** the window's width equals the UTC offset and
**disappears entirely for UTC and negative-offset zones. A test written in CI (typically UTC) would
never observe it.**

## Deliverables

1. **D1 — GATE (mutates nothing): settle intent, then reachability.** ⚠ **Confirm the local-time
   choice at line 131 was not deliberate** (e.g. intended to give operators human-local lesson ids)
   before changing it. Then determine whether the collision / miss in sequence allocation is actually
   reachable, and whether the off-by-one age materializes.
2. **D2 — converge the clocks.** If D1 finds the local choice accidental: make line 131 UTC, matching
   the file's other five sites and the repo-wide convention. **If it was deliberate, the fix is the
   INVERSE** — keep line 131 and label the id's zone explicitly. ⛔ **Either way the two must not stay
   silently divergent.**
3. **D3 — a test that pins the behaviour under a non-UTC `TZ`.** This is what makes the window
   visible; a UTC-only test proves nothing about this defect. Verify it fails pre-fix under a
   positive-offset `TZ`.

Three deliverables — small and tightly coupled.

## Why it belongs to this epic

Theme match — **confident-signal-hides-a-caveat.** A lesson id carries a date prefix that reads as
authoritative provenance: *"this lesson was filed on 2026-07-29."* The retention subsystem
simultaneously holds that the same lesson was filed on `2026-07-28`. **Both signals are emitted
confidently, neither is labelled with its zone, and nothing in the id or the tombstone reveals that
two different clocks produced them.**

It is also a **zone-invisible-under-test** case, adjacent to the epic's population-derived-detector
concern: correctness depends on the runner's timezone, so **a green CI run is not evidence the paths
agree.**

## Claim Labels

- OBSERVED (message-supplied with line numbers): line 131 local; lines 293/411/804/1011/1085 UTC.
  ⚠ **Verify by SYMBOL, not line number** — the file has changed recently (#1039 landed
  `manage-lessons` work).
- OBSERVED: the repo-wide UTC convention across the seven named producers.
- HYPOTHESIS: the sequence-allocation collision/miss is reachable — confirm/refute at the
  id-allocation function against the retention comparison (verify-at-outline). **Refutation does not
  kill the plan**; it re-scopes D2 to a consistency fix with the reachability finding recorded.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/manage-lessons.py`
- OBSERVED: the `manage-lessons` test module under `test/plan-marshall/manage-lessons/`

## Dependencies and Sequencing

- Depends on: none. ✅ **Unblocked** — PLAN-90 (`lessons-corpus-is-written-and-never-read`) shipped as
  #1039.
- Overlaps with: ⛔ **PLAN-103 (`wrong-store-guard-refuses-project-local-lessons`) edits the SAME
  FILE.** **Sequence, never pair.** PLAN-103 is ahead in the queue — run it first.
- Adjacent to: PLAN-65 (`landed-residue-promotion-sweep`) reads the lessons corpus but does not edit
  this script.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-109-manage-lessons-mixes-local-time-and-utc.md"
```

## Write-Boundary

Repository source + tests only; NO `.plan/local/orchestrator/` writes other than this plan's own
`inbox/{sender}-{seq}` message. See orchestration-model.md § Ledger Write-Boundary.
