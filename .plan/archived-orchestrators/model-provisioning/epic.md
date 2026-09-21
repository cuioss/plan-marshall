# Epic: Execution-context model provisioning (machine-local)

slug: model-provisioning

> Ledger document for one epic under `.plan/orchestrator/model-provisioning/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Re-establish per-level model provisioning for `execution-context` variants: the effort-to-model
map must be machine-local (each user has a different setup — local models as well as provider
configs such as Zen and Go), and a dedicated OpenCode marshall-steward step materializes per-level
pins from it. This reverses the inherit-only posture of commit `2ec552ba4` deliberately, not by
drift: the re-enable direction, the local-map schema (with an entry-kind discriminator, since a
bare model string does not say local vs provider-routed), and its slot in the effort resolve chain
are all settled before the steward step is built. Too large for one plan because it spans a
config-schema decision, a resolve-chain seam change, and a steward-step implementation with
live-client verification per entry kind. Done is: each dispatch level resolves to the user's
configured model (local or provider) through the local map, with the narrow-but-never-escalate
posture enforced and verified red-first.

## Provenance and sequencing

- Follows the `tooling-truthfulness` effort-lever Watch (commit `2ec552ba4` + billing balance):
  the Watch's re-check trigger (billing topped up + explicit re-enable direction) fires FIRST —
  this epic builds on the re-enable decision, never ahead of it.
- Sequence inside the epic: (1) local-map schema + resolve-chain slot, (2) marshall-steward step
  consuming it, (3) live-client verification per entry kind (local model + provider config).
- `parallelization_scope` is **1** (operator answer on first init): machinery changes run
  strictly sequentially.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug model-provisioning
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: All 4 plans shipped (#1490/#1499/#1500/#1503). NEXT: close the epic on operator word.
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 18 archived
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-01) — plan=implement-plan-01-model-provisioning — PR 1490 — landing=landings/PLAN-01.md — status: shipped
- PLAN-02 (WS-02) — plan=implement-plan-02-steward-pin-materialization — PR 1499 — landing=landings/PLAN-02.md — status: shipped
- PLAN-03 (WS-02) — plan=implement-plan-03-emitter-reenable — PR 1500 — landing=landings/PLAN-03.md — status: shipped
- PLAN-04 (WS-03) — plan=plan-04-live-verification — PR 1503 — landing=landings/PLAN-04.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated markers.
     A regeneration replaces only what sits BETWEEN the markers, so everything written
     here survives it. -->

- (none yet)

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug model-provisioning (paste it verbatim after a
     queue change), and rewritten in place by the compact stage at cleanup. Only the LIVE
     queue is rendered here. Per-row notes a reader wants to ADD go in the annotation zone
     below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

<!-- ANNOTATION ZONE — hand-written, and deliberately OUTSIDE the generated table markers. -->

- (none yet)

## Decisions

- 2026-09-13 — **Epic home is a fresh epic** (`model-provisioning`), not a `multiplattform`
  follow-up or a `tooling-truthfulness` add-on: model provisioning is its own subject.
  Zen/Go are OpenCode provider-config entries; local models are covered as a second entry
  kind with a schema-level kind discriminator. Recorded from operator Q&A; full trail in
  `tooling-truthfulness` decision log.
- 2026-09-13 — **`parallelization_scope` = 1** (operator answer on first init, Branch A).
- 2026-09-14 — **PLAN-01 shipped as #1490** (squash `fb8aadc9`, report
  `landings/PLAN-01.md`). ADR-021 + 3 contract sections + comment-only seam
  note, all corroborated at HEAD; 1 loop-back fix (CodeRabbit 1d63a7, ADR risk
  wording), 3 accepts;   review barrier clean, merge queue landed it. Prior
  #1485 closed unmerged (CodeRabbit quota-refusal) to re-trigger bot
  participation. PLAN-02's sequencing hold lifts — schema + slot settled.
- 2026-09-14 — **Inbox drained 2/2** (landing-check complete on the landing
  message; candidate-lesson promoted to corpus `2026-09-14-12-001`:
  ci-timeout acceptance recurrence as plan-marshall architecture hint).
- 2026-09-14 — **Inherit fallback is unconditional** (operator invariant, mid-PLAN-02):
  unconfigured local-model pins always resolve inherit-only. Already in PLAN-02/03/04
  scope; enforced at PLAN-02 landing analysis.
- 2026-09-15 — **PLAN-02 shipped as #1499** (squash `71a08925`, report
  `landings/PLAN-02.md`). Pin materialization (`effort_pins.py`, both entry kinds,
  inherit fallback, never-escalate) + menu/wizard wiring + tests, plus the
  operator-authorized argparse-surface-cache fix. Review barrier clean
  (CodeRabbit rounds fixed via TASK-6/7/8/9, sourcery approved), 2 loop-backs
  converged. PLAN-03 sequencing hold lifts — pin shape settled.
- 2026-09-16 — **PLAN-03 shipped as #1500** (merge queue `793300a9`, report
  `landings/PLAN-03.md`). Emitter re-enable (pin-present/pin-absent branches,
  both-kinds transform, emit-time never-escalate) + per-kind tests, plus a
  one-line ADR-021 cross-reference keep. Review barrier clean (2 CodeRabbit
  comments triaged, replies posted), 16h38m / 0 tokens (degraded capture,
  approved). PLAN-04 sequencing hold lifts — pins are threadable.
- 2026-09-16 — **Inbox drained 15/15** (14 candidate-lessons + 1 landing, all
  live/valid): landing reconciled; `*-003` promoted to corpus
  `2026-09-16-11-001` (OpenCode token-capture gap); `*-001/002/011/012/013/014`
  discarded as recurrence of corpus `2026-09-12-17-001`
  (+ `2026-09-11-19-001`); `*-004` discarded as recurrence of
  `2026-09-02-13-005`; `*-005/006/007` discarded (single-instance mypy
  defects, fixed in-run via TASK-008); `*-008/009/010` discarded as
  self-declared duplicates of `005/006/007`.
- 2026-09-16 — **PLAN-04 shipped as #1503** (merge queue `ac981779`, report
  `landings/PLAN-04.md`). Verification-only (+112, single test file):
  5 live tests thread real steward output into the emit path, red-first,
  fallback + never-escalate asserted. One mypy fix in-run, second CI run
  green. Queue empty — epic ready for `close`.

## Open Defects

(none yet)

## Watches

- **Effort-lever re-enable is the entry precondition.** This epic builds only after the
  `tooling-truthfulness` Watch's re-check trigger fires (billing + explicit re-enable).
  Starting plan work before that decision reverses `2ec552ba4` without authorization. —
  *re-check trigger: operator confirms billing topped up and directs re-enabling.*
- **2 lesson proposals pending operator decision** (PLAN-02 residue, 2026-09-15):
  compose change-type + argparse-recurrence held report-only in the archived plan's
  `quality-verification-report.md` — record or drop on operator word.
