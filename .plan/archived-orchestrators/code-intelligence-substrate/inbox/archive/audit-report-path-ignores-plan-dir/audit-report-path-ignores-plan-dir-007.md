envelope_version=1
sender_type=plan
sender_id=audit-report-path-ignores-plan-dir
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-07-30T09:30:49Z

component=plan-marshall:marshall-orchestrator
category=improvement
title=inbox list cannot express "consumed" — two readers mis-read it in opposite directions in one session

# inbox list cannot express "consumed"

## Observation

`orchestrator inbox list --slug code-intelligence-substrate` returned `count: 1` for plan `audit-report-path-ignores-plan-dir`. The plan had in fact written **four** messages, exactly as its `lessons-capture` step reported. Three of them (`-002`, `-003`, `-004`) had been archived — consumed — between 08:09:34 and 08:11:37, leaving only the `kind=landing` `-001` queued.

`inbox list` deliberately excludes archived messages (that exclusion is what makes a re-scan of a completed drain a no-op), and **no CLI verb enumerates `inbox/archive/`**. `inbox validate` resolves only against `inbox/`, returning `file_not_found` for an archived message.

## Why this matters: it produced two opposite errors in one session

- The **dispatch brief** for the retrospective asserted "lessons-capture already wrote messages -001 (landing) through -004 there this run; do not duplicate those" — treating all four as present and queued.
- The **retrospective itself** read `count: 1`, found the three candidate-lesson payloads still staged on disk, and concluded they had been silently lost. It filed that as a high-severity finding and **re-delivered a duplicate** (`-005`) before catching itself.

The tell was the sequence allocator: the re-delivery was handed `-005`, not `-002`. A counter at 005 is only reachable if 002-004 already existed. A direct filesystem probe of `inbox/archive/` then confirmed all three, byte-size-matched to the staged payloads. The duplicate `-005` was retired via `inbox archive`.

## Mechanism

The read surface has two states (`queued`, `absent`) for an underlying three-state reality (`queued`, `consumed`, `never written`). `consumed` and `never written` both render as absence. Neither reader was careless — the surface genuinely cannot answer the question either of them was asking.

## Rule

- Add `--include-archived` to `inbox list` (mirroring `manage-findings list --include-qgate`, which solved the identical problem for the findings store), or report an `archived_count` alongside `count`.
- Until then: **`inbox list` returning a low count is not evidence that messages were not written.** Check the sequence allocator or the archive before concluding non-delivery, and never re-deliver on the strength of a `count` read alone.
- Archival is currently unlogged. Three messages were consumed inside the finalize window with no log entry naming the actor or the event; reconstructing what happened required reading filesystem mtimes. The archive verb should emit a work-log line.

## Relation to the epic

This is the epic's own theme turned back on the auditor. The retrospective auditing "confident signals that hide a caveat" produced exactly one: a confident `3 lessons lost` verdict derived from a read surface that cannot express the state it was being asked about. The finding was retracted before it shipped, but only because an incidental detail — a sequence number — contradicted it.
