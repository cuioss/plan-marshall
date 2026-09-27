envelope_version=1
sender_type=plan
sender_id=ledger-decomposition-and-row-vocabulary
epic=review-apparatus
kind=finding
created=2026-09-23T17:28:23Z

## Stale plan-status vocabulary in `review-apparatus/epic.md`

`epic.md` still asserts the retired six-member row-status vocabulary in three passages. The vocabulary
they describe is no longer the one `orchestrator.py` enforces, so each passage now tells a reader
something false about what the queue can express. Reported by plan
`ledger-decomposition-and-row-vocabulary` (orchestrator-refactor PLAN-02), which owns the row-vocabulary
reconciliation; the Ledger Write-Boundary forbids it from editing this ledger, so the correction is
yours to apply.

### The current vocabulary (declaring source)

`VALID_STATUS_VOCABULARY` in `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py`
is the union of `LIVE_PLAN_STATUSES`, `SHIPPED_PLAN_STATUSES` and `CLOSED_UNSHIPPED_PLAN_STATUSES`. The
closed-unshipped set is `superseded`, `transferred`, `retired`, `resolved`. `queue --transition --status`
validates against the full set, so all four are writable today, and all four are TERMINAL — a row at any
of them is left out of the Ordered Queue. Meanings are in
`persona-plan-orchestrator/standards/orchestration-model.md` § Plan-Status Vocabulary.

### Stale passage 1 — § Ordered Queue → the per-row narrative zone after `### Queue annotations`

> ⛔⛔ **PLAN-PR-025 IS RETIRED AND SUPERSEDED (2026-08-29) — the mandatory split is DONE.** Do not
> re-split it and do not emit it. Its row rides the live queue only because `retired` is not terminal.

`retired` IS terminal now. The generated Ordered Queue at HEAD already omits PLAN-PR-025, so the stated
reason is false and the row does not ride the live queue.

### Stale passage 2 — same zone

> PLAN-PR-018 and PLAN-PR-004 are retired; PLAN-PR-002 is parked on an open foreign PR
> (`cuioss-organization#235`). All three ride the live queue because they are not terminal.

True only for PLAN-PR-002 (`parked` is live). PLAN-PR-018 and PLAN-PR-004 are `retired`, which is
terminal; neither appears in the generated Ordered Queue at HEAD.

### Stale passage 3 — § Open Defects → "REDISTRIBUTION 2026-09-12"

> ⛔⛔ **THE 18 SUPERSEDED ROWS ARE RECORDED `parked`, AND THAT IS NOT WHAT THEY ARE.** The queue cannot
> express `retired`: `orchestrator.py`'s `VALID_STATUS_VOCABULARY` is
> `{staged, launched, running, parked, shipped, landed}` and `--transition` refuses `retired` with
> `invalid_field` — **while four rows in this very ledger already carry it** (`PLAN-PR-004`, `-018`,
> `-025`, `-028`, written by the unvalidated bulk rewrite before the single-row forms existed). `parked`
> is the only expressible non-emittable state and `next` walks `staged` only, so the queue is SAFE; it is
> not TRUE.

The six-member set and the `invalid_field` refusal are both retired. `--transition --status superseded`
(and `retired`) now succeeds. The four `retired` rows are valid, not an unvalidated-bulk-rewrite artefact.
The "filed to `truthful-signals` as `review-apparatus-036.md` … not this epic's to fix" sentence that
follows is answered: the vocabulary landed via PLAN-TRUTH-143 (#1539).

### Suggested reconciliation (your decision)

1. Transition the rows the 2026-09-12 redistribution recorded as `parked` stand-ins for superseded specs
   to `superseded`, one `queue --transition` per row, so the queue becomes TRUE as well as SAFE.
2. Rewrite passages 1 and 2 so they no longer claim `retired` rows ride the live queue.
3. Mark passage 3's vocabulary sentence as resolved rather than current.
