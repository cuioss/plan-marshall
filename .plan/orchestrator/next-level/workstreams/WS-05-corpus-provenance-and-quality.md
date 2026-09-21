# WS-05: Corpus provenance and quality

epic: next-level

> Charter document for one workstream. Lives at `workstreams/WS-05-corpus-provenance-and-quality.md` and
> is tracked in the epic `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

Cut during the 2026-09-14 inbox drain, from `next-level-009` and `next-level-010`.

## Charter

The other four workstreams measure the *authored* substrate — skills, standards, workflow docs. This one
covers the substrate that **accumulates**: the lessons corpus, which steers every session and which
nothing has ever measured. It has no provenance record, no freshness term, no confidence between live and
retired, and no number stating what share of it is accurate, relevant, or load-bearing. It closes when
the corpus has a precision figure derived against an enumerated golden set, and a recorded decision on
whether the mechanisms that figure implies are worth building.

## Scope

- In scope: the lessons store's schema and lifecycle surface; a provenance field; a precision measurement
  against a golden set; the decision on a moving confidence and on regeneration-over-trim.
- Out of scope: ⛔ **any deletion, retirement, or bulk mutation of the corpus.** This workstream measures
  and adds; it never prunes. The store carries tombstones whose loss is unrecoverable and a removal verb
  with a recorded destroy-while-reporting-`not_found` failure mode. Also out of scope: the routing role
  of the lessons-handling epics, which this workstream serves rather than replaces.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-09-lessons-corpus-provenance-and-quality | staged | Size the golden set, measure precision, add provenance, decide on the two absent mechanisms. |

## Sequencing and Surface Notes

- No dependency on any other workstream. Surface-disjoint from every other staged row — it touches
  `manage-lessons/` and its mirror test directory, which nothing else in the epic declares.
- ⚠ **The corpus itself is not in the declarable surface.** It lives in a git-ignored store outside the
  inventory, so the disjointness gate cannot see it and a concurrent lessons-handling epic working the
  same store would collide invisibly. Check for a live lessons epic before emitting, by hand — the gate
  will not do it.
- ⭐ The sizing deliverable precedes the measuring one, deliberately. A golden set is human labour, and
  this epic has already recorded, in PLAN-01, what an unbounded verification layer costs here.
