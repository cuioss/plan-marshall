# Epic: Test Quality — archived 2026-09-21

slug: test-quality-26-09-21

> Ledger document for one epic under `.plan/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Frozen snapshot of `test-quality`'s terminal plan history as of 2026-09-21, split out of
the live epic to keep the working queue small. Carries 25 terminal rows (test-authoring
standards, per-slice test-reduction sweeps, the module-budget campaign, and the
test-fidelity-rules landing) that were already shipped or landed before the split. See
`history.md` for the closing record. The live epic (`test-quality`) retains the still-open
rows (PLAN-140, PLAN-181).

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug test-quality-26-09-21
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: (not set)
**Phase**: init
**Inbox (derived)**: 0 queued, 0 archived
**Queue** (staged, in order):
- (empty)
- PLAN-010 (WS-01) — PR #1248, #1250 — landing=landings/PLAN-010.md — status: landed
- PLAN-020 (WS-01) — PR #1247 — landing=landings/PLAN-020.md — status: landed
- PLAN-030 (WS-02) — PR #1261, #1270 — landing=landings/PLAN-030.md — status: landed
- PLAN-040 (WS-02) — PR #1259 — landing=landings/PLAN-040.md — status: landed
- PLAN-050 (WS-02) — PR #1258, #1266 — landing=landings/PLAN-050.md — status: landed
- PLAN-060 (WS-02) — PR #1263, #1265, #1272 — landing=landings/PLAN-060.md — status: landed
- PLAN-070 (WS-02) — PR #1290 — landing=landings/PLAN-070.md — status: landed
- PLAN-080 (WS-02) — PR #1302, #1306 — landing=landings/PLAN-080.md — status: landed
- PLAN-090 (WS-03) — PR #1294 — landing=landings/PLAN-090.md — status: landed
- PLAN-100 (WS-04) — PR #1314 — landing=landings/PLAN-100.md — status: landed
- PLAN-105 (WS-04) — plan=every-module-counts-and-the-campaign-can-finish — PR #1407 — landing=landings/PLAN-105.md — status: shipped
- PLAN-110 (WS-05) — plan=every-test-runs-and-the-suite-does-not-slow-down — PR #1426 — landing=landings/PLAN-110.md — status: shipped
- PLAN-120 (WS-06) — plan=derive-the-partition-and-the-budget-attribution — PR #1345 — landing=landings/PLAN-120.md — status: shipped
- PLAN-130 (WS-02) — plan=plan-130-sweep-the-prose-the-widened-rules — PR #1436, #1435 — landing=landings/PLAN-130.md — status: shipped
- PLAN-135 (WS-02) — plan=sweep-preambles-shipped-accessors — PR #1446 — landing=landings/PLAN-135.md — status: shipped
- PLAN-145 (WS-03) — plan=plan-145-publish-the-missing-parser-seams — PR #1395 — landing=landings/PLAN-145.md — status: shipped
- PLAN-150 (WS-02) — plan=plan-150-close-the-namespace-conversion — PR #1383 — landing=landings/PLAN-150.md — status: shipped
- PLAN-155 (WS-02) — plan=close-the-runtime-slice-parametrization — PR #1455 — landing=landings/PLAN-155.md — status: shipped
- PLAN-160 (WS-03) — plan=sweep-the-three-single-instance-defect-classes — PR #1486 — landing=landings/PLAN-160.md — status: shipped
- PLAN-165 (WS-03) — plan=implement-plan-165-close-orphan-defects — PR #1480 — landing=landings/PLAN-165.md — status: shipped
- PLAN-170 (WS-06) — plan=plan-170-make-the-attribution-usable — PR #1385 — landing=landings/PLAN-170.md — status: shipped
- PLAN-175 (WS-03) — plan=harden-the-shipped-shape-scanners — PR #1506 — landing=landings/PLAN-175.md — status: shipped
- PLAN-176 (WS-04) — plan=module-budget-campaign-run-2-slice-040 — PR #1514,#1515,#1526,#1517,#1518,#1519,#1520,#1521,#1522 — landing=landings/PLAN-176.md — status: shipped
- PLAN-177 (WS-03) — plan=close-the-leftover-gate-gaps — PR #1534 — landing=landings/PLAN-177.md — status: shipped
- PLAN-180 (WS-01) — plan=test-fidelity-rules — PR #1538, #1549 — landing=landings/PLAN-180.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

- All 25 rows are terminal (15 shipped, 10 landed) — nothing live in this archive by design.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug test-quality-26-09-21 (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug test-quality-26-09-21) at
     cleanup. Only the LIVE queue is rendered here — a row at any TERMINAL status is left
     out, whether it shipped or closed without shipping; see the standard's
     § Plan-Status Vocabulary. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
<!-- END GENERATED: ordered-queue -->

(Empty by design — every row in this archive is terminal, so none appears in the live queue.)

### Queue annotations

- None — no live rows.

## Decisions

- 2026-09-21 — Split from the live `test-quality` epic as part of a fleet-wide orchestrator
  restructuring pass (operator-directed). All 25 terminal rows (shipped/landed) relocated
  here verbatim with their original ids, slugs, and landing links; the 2 live rows
  (PLAN-140 parked, PLAN-181 staged) remained in `test-quality`. No content was altered.

## Open Defects

- None carried forward — this is a closed historical record.

## Watches

- None — closed epic.
