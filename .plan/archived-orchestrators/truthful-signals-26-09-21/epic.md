# Epic: Truthful Signals — archived 2026-09-21

slug: truthful-signals-26-09-21

> Ledger document for one epic under `.plan/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Frozen snapshot of `truthful-signals`' terminal plan history as of 2026-09-21 (196 rows:
shipped, superseded, transferred, retired), plus `quality-aspect`'s terminal history (3
shipped rows, merged in on this date and renumbered PLAN-204/210/212 — quality-aspect is
fully absorbed into truthful-signals; see quality-aspect's own `history.md` for that
epic's closing record). This epic holds no live work — it exists purely as the audit
record for work already landed or otherwise closed. "Done" for this epic is: nothing,
it is already closed.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug truthful-signals-26-09-21
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: Archived snapshot of truthful-signals' terminal history as of 2026-09-21 (196 rows) plus quality-aspect's 3 terminal rows (merged in on this date, renumbered PLAN-204/210/212). Read-only historical record.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 0 archived
**Queue** (staged, in order):
- (empty — all 199 rows are terminal; see history.md for the outcome record)
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers. -->

- This epic is closed and archived. See `history.md` for the full outcome record.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Only the LIVE queue is rendered here — a row at any TERMINAL status is left
     out. Every row in this epic is terminal, so the table is empty by construction. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

- All 199 rows are terminal (shipped, superseded, transferred, or retired). See `history.md`.

## Decisions

- 2026-09-21 — Split truthful-signals into a live epic (`truthful-signals`, 29 rows +
  15 merged quality-aspect rows) and this dated archive (196 truthful-signals terminal
  rows + 3 quality-aspect terminal rows). quality-aspect merged into truthful-signals in
  full — same "confident signal hides a caveat" defect archetype, scoped to the finalize
  lane. Alternative considered: leave quality-aspect as an independent sibling epic;
  rejected because the archetype identity made the two indistinguishable in practice.

## Open Defects

(none carried forward here — any still-open defect belonging to a terminal row is
recorded in that row's own landing document under `landings/`.)

## Watches

(none — this epic is closed.)
