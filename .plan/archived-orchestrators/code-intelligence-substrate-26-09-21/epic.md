# Epic: Code Intelligence Substrate — archived 2026-09-21

slug: code-intelligence-substrate-26-09-21

> Ledger document for one epic under `.plan/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Frozen snapshot of `code-intelligence-substrate`'s terminal plan history as of 2026-09-21. This epic carries no live queue of its own — it exists solely as the audit record for the 56 rows (54 shipped, 2 retired) split out of the live epic during the 2026-09-21 orchestrator restructuring. See `history.md` for the closing rationale and `../code-intelligence-substrate/epic.md` for the epic that continues this work.

## START HERE

<!-- GENERATED BLOCK — never hand-write or hand-edit this section.
     Regenerate after every queue-touching state change via:
     python3 .plan/execute-script.py plan-marshall:plan-orchestrator:orchestrator resume-summary --slug code-intelligence-substrate-26-09-21
     Paste the returned `summary` block verbatim between the markers (the same
     invocation also emits `ordered_queue` for the Ordered Queue section below).
     Anything a reader wants to add BY HAND goes in the annotation zone below,
     outside the markers — never inside them. -->

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: (not set)
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 0 archived
**Queue** (staged, in order):
- (empty)
- PLAN-01 (WS-01) — plan=inventory-blind-spot — PR 1056 — landing=landings/PLAN-01.md — status: shipped
- PLAN-10 (WS-04) — plan=end-phase-replace-not-accumulate — PR 1059 — landing=landings/PLAN-10.md — status: shipped
- PLAN-11 (WS-05) — plan=audit-report-path-ignores-plan-dir — PR 1063 — landing=landings/PLAN-11.md — status: shipped
- PLAN-02 (WS-02) — plan=resolver-ext-point-seam — PR 1067 — landing=landings/PLAN-02.md — status: shipped
- PLAN-CIS-023 (WS-01) — plan=path-attribution-seam — PR 1072 — landing=landings/PLAN-CIS-023.md — status: shipped
- PLAN-CIS-003 (WS-02) — plan=marketplace-dependency-resolver — PR 1074 — landing=landings/PLAN-CIS-003.md — status: shipped
- PLAN-CIS-027 (WS-02) — plan=plan-cis-027-graph-merge-drops-every-resolver-edge — PR 1079 — landing=landings/PLAN-CIS-027.md — status: shipped
- PLAN-CIS-028 (WS-04) — plan=post-run-steps-ordered-before-their-evidence — PR 1080 — landing=landings/PLAN-CIS-028.md — status: shipped
- PLAN-CIS-030 (WS-04) — plan=context-byte-attribution-instrumentation — PR 1086 — landing=landings/PLAN-CIS-030.md — status: shipped
- PLAN-CIS-001 (WS-01) — plan=content-search-seam — PR 1084 — landing=landings/PLAN-CIS-001.md — status: shipped
- PLAN-CIS-009 (WS-04) — PR 1100 — landing=landings/PLAN-CIS-009.md — status: shipped
- PLAN-CIS-021 (WS-05) — PR 1107 — landing=landings/PLAN-CIS-021.md — status: shipped
- PLAN-CIS-031 (WS-04) — plan=self-review-resweeps-full-surface-every-round — PR 1126 — landing=landings/PLAN-CIS-031.md — status: shipped
- PLAN-CIS-032 (WS-01) — plan=executor-rejects-invalid-invocations-before-spawn — PR 1127 — landing=landings/PLAN-CIS-032.md — status: shipped
- PLAN-CIS-041 (WS-03) — PR 1140 — landing=landings/PLAN-CIS-041.md — status: shipped
- PLAN-CIS-042 (WS-04) — PR 1154 — landing=landings/PLAN-CIS-042.md — status: shipped
- PLAN-CIS-045 (WS-05) — PR 1164 — landing=landings/PLAN-CIS-045.md — status: shipped
- PLAN-CIS-034 (WS-04) — PR 1175 — landing=landings/PLAN-CIS-034.md — status: shipped
- PLAN-CIS-037 (WS-04) — PR 1173 — landing=landings/PLAN-CIS-037.md — status: shipped
- PLAN-CIS-035 (WS-04) — PR 1180 — landing=landings/PLAN-CIS-035.md — status: shipped
- PLAN-CIS-040 (WS-06) — PR 1185 — landing=landings/PLAN-CIS-040.md — status: shipped
- PLAN-CIS-043 (WS-05) — PR 1189 — landing=landings/PLAN-CIS-043.md — status: shipped
- PLAN-CIS-044 (WS-05) — PR 1199 — landing=landings/PLAN-CIS-044.md — status: shipped
- PLAN-CIS-024 (WS-01) — PR 1201 — landing=landings/PLAN-CIS-024.md — status: shipped
- PLAN-CIS-002 (WS-02) — PR 1207 — landing=landings/PLAN-CIS-002.md — status: shipped
- PLAN-CIS-025 (WS-01) — PR 1208 — landing=landings/PLAN-CIS-025.md — status: shipped
- PLAN-CIS-029 (WS-01) — PR 1216 — landing=landings/PLAN-CIS-029.md — status: shipped
- PLAN-CIS-033 (WS-01) — PR 1220 — landing=landings/PLAN-CIS-033.md — status: shipped
- PLAN-CIS-010 (WS-04) — PR 1225 — landing=landings/PLAN-CIS-010.md — status: shipped
- PLAN-CIS-011 (WS-04) — PR 1232 — landing=landings/PLAN-CIS-011.md — status: shipped
- PLAN-CIS-038 (WS-04) — PR 1236 — landing=landings/PLAN-CIS-038.md — status: shipped
- PLAN-CIS-026 (WS-02) — PR 1243 — landing=landings/PLAN-CIS-026.md — status: shipped
- PLAN-CIS-004 (WS-02) — PR 1238 — landing=landings/PLAN-CIS-004.md — status: shipped
- PLAN-CIS-005 (WS-02) — PR 1252 — landing=landings/PLAN-CIS-005.md — status: shipped
- PLAN-CIS-006 (WS-03) — PR 1254 — landing=landings/PLAN-CIS-006.md — status: shipped
- PLAN-CIS-007 (WS-03) — PR 1256 — landing=landings/PLAN-CIS-007.md — status: shipped
- PLAN-CIS-012 (WS-04) — PR 1268 — landing=landings/PLAN-CIS-012.md — status: shipped
- PLAN-CIS-013 (WS-04) — PR 1271 — landing=landings/PLAN-CIS-013.md — status: shipped
- PLAN-CIS-014 (WS-04) — PR 1260 — landing=landings/PLAN-CIS-014.md — status: shipped
- PLAN-CIS-015 (WS-05) — PR 1283 — landing=landings/PLAN-CIS-015.md — status: shipped
- PLAN-CIS-016 (WS-05) — PR 1276 — landing=landings/PLAN-CIS-016.md — status: shipped
- PLAN-CIS-017 (WS-05) — PR 1279 — landing=landings/PLAN-CIS-017.md — status: shipped
- PLAN-CIS-018 (WS-04) — PR 1286 — landing=landings/PLAN-CIS-018.md — status: shipped
- PLAN-CIS-019 (WS-04) — PR 1288 — landing=landings/PLAN-CIS-019.md — status: shipped
- PLAN-CIS-020 (WS-04) — PR 1287 — landing=landings/PLAN-CIS-020.md — status: shipped
- PLAN-CIS-022 (WS-04) — PR 1293 — landing=landings/PLAN-CIS-022.md — status: shipped
- PLAN-CIS-046 (WS-02) — PR 1214 — landing=landings/PLAN-CIS-046.md — status: shipped
- PLAN-CIS-047 (WS-05) — PR 1295 — landing=landings/PLAN-CIS-047.md — status: shipped
- PLAN-CIS-048 (WS-07) — PR 1321 — landing=landings/PLAN-CIS-048.md — status: shipped
- PLAN-CIS-059 (WS-02) — plan=fold-pm-code-intelligence-into-core — PR 1348 — landing=landings/PLAN-CIS-059.md — status: shipped
- PLAN-CIS-060 (WS-07) — plan=verdict-field-read-and-write-integrity — PR 1355 — landing=landings/PLAN-CIS-060.md — status: shipped
- PLAN-CIS-051 (WS-07) — plan=detector-and-auditor-integrity — PR 1370 — landing=landings/PLAN-CIS-051.md — status: shipped
- PLAN-CIS-049 (WS-07) — plan=architecture-store-query-truthfulness — PR 1489 — landing=landings/PLAN-CIS-049.md — status: shipped
- PLAN-CIS-053 (WS-07) — plan=test-suite-anti-vacuity — PR 1443 — landing=landings/PLAN-CIS-053.md — status: shipped
- PLAN-CIS-008 (WS-04) — status: retired
- PLAN-CIS-055 (WS-07) — status: retired
<!-- END GENERATED: resume-summary -->

### Annotations

- None — this is a frozen archive; the live epic carries forward all annotations.

## Ordered Queue

<!-- GENERATED BLOCK — never hand-write or hand-edit the table between the markers.
     Regenerated from status.json and the staged specs: emitted as `ordered_queue` by
     orchestrator.py resume-summary --slug code-intelligence-substrate-26-09-21 (paste it verbatim after a queue change),
     and rewritten in place by the compact stage (orchestrator.py compact --slug code-intelligence-substrate-26-09-21) at
     cleanup. Only the LIVE queue is rendered here — a row at any TERMINAL status is left
     out, whether it shipped or closed without shipping; see the standard's
     § Plan-Status Vocabulary. Per-row notes a reader wants to ADD go in the
     annotation zone below, outside the markers — never inside them. -->

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

- None — the live queue is empty by design; every row here is terminal.

## Decisions

- 2026-09-21 — Split from `code-intelligence-substrate` as part of an operator-directed orchestrator restructuring: 56 terminal rows (54 shipped, 2 retired) frozen here; 9 live rows (3 staged, 6 parked) remain in the live epic.

## Open Defects

- None carried here — any open defect surfaced by a landing in this set that is not yet resolved travels with the live epic's own Open Defects section, not this archive.

## Watches

- None — a frozen archive accrues no new watches.
