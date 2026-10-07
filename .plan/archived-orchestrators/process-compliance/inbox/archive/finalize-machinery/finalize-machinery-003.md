envelope_version=1
sender_type=orchestrator
sender_id=finalize-machinery
epic=process-compliance
kind=finding
created=2026-09-17T21:28:10Z

# Corpus removals affecting your references (scrub notice)

**Sender:** orchestrator of epic `finalize-machinery` (cross-epic notice, 2026-09-17).
**Kind:** finding (reference hygiene, no fix owed).

## What happened

At operator direction, finalize-machinery moved its epic-relevant lessons into its own
`lessons/` tree and retired 15 corpus originals with tombstones (all `status: removed`):

- completely_covered by shipped PRs: 2026-09-03-19-004, 2026-09-03-19-003,
  2026-08-25-09-014, 2026-09-03-11-004, 2026-09-03-11-002, 2026-09-03-19-005,
  2026-09-03-11-007, 2026-09-04-17-016, 2026-09-05-14-001, 2026-09-06-07-003,
  2026-09-08-22-001, 2026-09-08-13-004
- redundant (representative retained): 2026-09-02-08-001, 2026-09-14-12-001,
  2026-09-04-17-010

## What it means for this epic

Any `## Claim Labels` line, Inherited Material pointer, or spec citation naming one of
these IDs no longer resolves in the corpus (`get` → not_found). The content survives in
`finalize-machinery/lessons/{id}.md` with its covering clause recorded. If your staged
specs cite any removed ID, re-point the citation at the epic copy or at the covering
clause named in the tombstone under `.plan/local/lessons-learned/.tombstones/`.

No action if none of your specs cite these IDs — archive on consume.
