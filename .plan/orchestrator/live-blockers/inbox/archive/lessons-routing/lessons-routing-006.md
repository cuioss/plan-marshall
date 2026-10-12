envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=live-blockers
kind=finding
created=2026-10-09T15:43:48Z

# scope_creep_check fails with exit 1 and empty stderr (fourth recurrence)

- **Severity:** high by frequency (`backlog.md` § 1.7)
- **Bundle:** `plan-marshall` (`phase-5-execute`)
- **Source lesson:** `2026-10-07-12-002`
- **Full body:** `lessons-routing/lessons-archive/filed-live-blockers/2026-10-07-12-002.md`
- **Filed by:** the `ingest` run of `lessons-routing`, 2026-10-09 (second run). The lesson is retired from the corpus.

## What the lesson says

In plan `issue-1697` (2026-10-07) `scope_creep_check check` failed five times across 5-execute with
exit 1 and an empty stderr. Proposed: surface the underlying exception instead of swallowing it.

## Owner today

PLAN-LB-27 (staged) owns the scope-creep guard; `lessons-routing-002` and three plan messages were
already folded into it. This is one more sighting of the same crash.

## Asked of live-blockers

Check for a residual only: PLAN-LB-27's first deliverable fixes why the guard exits 1; confirm it
also makes a failing call say why (a non-empty error), which is the one thing this lesson adds.
Not re-checked in code at this run — PLAN-LB-27 has not shipped, so the defect is taken as live.
