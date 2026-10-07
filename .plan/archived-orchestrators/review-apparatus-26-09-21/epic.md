# Epic: Review Apparatus — Archived 2026-09-21

slug: review-apparatus-26-09-21

> Ledger document for one epic under `.plan/orchestrator/{slug}/`. The layout and
> authority contract live in the central standard — see
> `persona-plan-orchestrator/standards/orchestration-model.md`. `status.json` is the
> machine authority; any statement here that conflicts with it is stale prose.

## Vision

Frozen snapshot of `review-apparatus`' terminal plan history as of 2026-09-21. It carries
the 38 rows that had already reached a terminal state (shipped, retired) when the live
epic's queue was split so `review-apparatus` could restart with only its 40 live rows.
No new work is staged here — see `history.md` for the outcome record.

## START HERE

<!-- BEGIN GENERATED: resume-summary -->
**Resume anchor**: (not set)
**Phase**: orchestrating
**Inbox (derived)**: 0 queued, 0 archived
**Queue** (staged, in order):
- (empty)
- PLAN-PR-014 (WS-04) — plan=crashed-participation-gate-records-a-pass — PR 1070 — landing=landings/PLAN-PR-014.md — status: shipped
- PLAN-PR-015 (WS-04) — plan=barrier-override-not-head-bound — PR 1077 — landing=landings/PLAN-PR-015.md — status: shipped
- PLAN-PR-016 (WS-03) — plan=correct-review-scores-as-maximally-wrong — PR 1078 — landing=landings/PLAN-PR-016.md — status: shipped
- PLAN-PR-001 (WS-01) — plan=wait-for-comments-counts-rows — PR 1071 — landing=landings/PLAN-PR-001.md — status: shipped
- PLAN-PR-009 (WS-04) — plan=merge-queue-enqueue-does-not-take — PR 1087 — landing=landings/PLAN-PR-009.md — status: shipped
- PLAN-PR-022 (WS-03) — plan=generic-charter-language-specific-defect — PR 1130 — landing=landings/PLAN-PR-022.md — status: shipped
- PLAN-PR-013 (WS-01) — plan=cloud/010-participation-credited-from-a-superseded-commit — PR 1141 — landing=landings/PLAN-PR-013.md — status: shipped
- PLAN-PR-023 (WS-02) — plan=cloud/020-a-foreign-task-reports-done-with-no-pr-anywhere — PR 1151 — landing=landings/PLAN-PR-023.md — status: shipped
- PLAN-PR-017 (WS-03) — plan=cloud/030-a-workflow-doc-prescribes-a-flag-no-script-declares — PR 1157 — landing=landings/PLAN-PR-017.md — status: shipped
- PLAN-PR-006 (WS-01) — plan=cloud/040-canned-no-op-indistinguishable-from-a-review — PR 1165 — landing=landings/PLAN-PR-006.md — status: shipped
- PLAN-PR-021 (WS-03) — plan=cloud/050-coverage-shortfall-disclosed-against-the-roster-not-the-required-set — PR 1170 — landing=landings/PLAN-PR-021.md — status: shipped
- PLAN-PR-018 (WS-03) — status: retired
- PLAN-PR-020 (WS-04) — plan=cloud/060-a-prose-routing-table-is-not-an-enforcement-boundary — PR 1182 — landing=landings/PLAN-PR-020.md — status: shipped
- PLAN-PR-019 (WS-03) — plan=cloud/070-post-responses-retransmits-already-sent-replies — PR 1187 — landing=landings/PLAN-PR-019.md — status: shipped
- PLAN-PR-007 (WS-01) — plan=absent-names-two-states-with-opposite-remedies — PR 1118 — landing=landings/PLAN-PR-007.md — status: shipped
- PLAN-PR-010 (WS-04) — plan=cloud/080-landing-message-carries-the-outcome-post-merge — PR 1196 — landing=landings/PLAN-PR-010.md — status: shipped
- PLAN-PR-012 (WS-03) — plan=cloud/090-feed-pr-findings-back-into-local-review — PR 1204 — landing=landings/PLAN-PR-012.md — status: shipped
- PLAN-PR-003 (WS-03) — plan=cloud/100-coderabbit-ai-agent-block-strip-vs-extract — PR 1212 — landing=landings/PLAN-PR-003.md — status: shipped
- PLAN-PR-005 (WS-01) — plan=cloud/110-participation-derived-from-a-lossy-view — PR 1219 — landing=landings/PLAN-PR-005.md — status: shipped
- PLAN-PR-008 (WS-04) — plan=cloud/120-review-barrier-deadlocks-on-a-refusing-bot — PR 1241 — landing=landings/PLAN-PR-008.md — status: shipped
- PLAN-PR-011 (WS-03) — plan=cloud/130-review-bots-catch-what-in-house-gates-cannot — PR 1239 — landing=landings/PLAN-PR-011.md — status: shipped
- PLAN-PR-004 (WS-03) — status: retired
- PLAN-PR-027 (WS-04) — plan=a-failing-ci-call-reports-success — PR 1356 — landing=landings/PLAN-PR-027.md — status: shipped
- PLAN-PR-024 (WS-01) — plan=participation-credit-anchored-to-merge-candidate — PR 1349 — landing=landings/PLAN-PR-024.md — status: shipped
- PLAN-PR-025 (WS-01) — status: retired
- PLAN-PR-025A (WS-01) — plan=a-refusal-is-recorded-as-a-refusal-the-record — PR 1368 — landing=landings/PLAN-PR-025A.md — status: shipped
- PLAN-PR-044 (WS-01) — plan=misconfigured-reviewer-name-reads-missing-review — PR 1392 — landing=landings/PLAN-PR-044.md — status: shipped
- PLAN-PR-042 (WS-03) — plan=required-reviewer-returns-empty-list — PR 1410 — landing=landings/PLAN-PR-042.md — status: shipped
- PLAN-PR-046 (WS-01) — plan=plan-pr-046 — PR 1477 — landing=landings/PLAN-PR-046.md — status: shipped
- PLAN-PR-025B (WS-01) — plan=arm-the-refusal-recovery-that-has-never-run — PR 1433 — landing=landings/PLAN-PR-025B.md — status: shipped
- PLAN-PR-032 (WS-02) — plan=apply-the-cloud-plan-lane-contract-amendments — PR 1416 — landing=landings/PLAN-PR-032.md — status: shipped
- PLAN-PR-034 (WS-01) — plan=a-refusal-nobody-recognises-is-filed-as-a-finding — PR 1344 — landing=landings/PLAN-PR-034.md — status: shipped
- PLAN-PR-036 (WS-03) — plan=exit-code-convention-stops-at-the-skill-boundary — PR 1423,1429 — landing=landings/PLAN-PR-036.md — status: shipped
- PLAN-PR-028 (WS-04) — status: retired
- PLAN-PR-033 (WS-04) — plan=the-foreign-gate-population-and-branch-f-recovery — PR 1473 — landing=landings/PLAN-PR-033.md — status: shipped
- PLAN-PR-038 (WS-03) — plan=review-packs-become-published-artifacts — PR 1388 — landing=landings/PLAN-PR-038.md — status: shipped
- PLAN-PR-041 (WS-03) — plan=NO_PLAN — PR cuioss/pr-agent-settings#15 — landing=landings/PLAN-PR-041.md — status: shipped
- PLAN-PR-065 (WS-02) — plan=pr-065-settings-repo-accumulates-never-lands — PR 1491 — landing=landings/PLAN-PR-065.md — status: shipped
<!-- END GENERATED: resume-summary -->

### Annotations

- Split from `review-apparatus` 2026-09-21 as part of the fleet-wide orchestrator restructuring.

## Ordered Queue

<!-- BEGIN GENERATED: ordered-queue -->
| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| — | (empty) | — | — | — |
<!-- END GENERATED: ordered-queue -->

### Queue annotations

- None — every row is terminal by construction of the split.

## Decisions

- 2026-09-21 — Split `review-apparatus` into a live epic (40 live rows) and this dated archive (38 terminal rows: 34 shipped, 4 retired), per operator-directed orchestrator restructuring. Landing files for the 34 shipped rows relocated here; workstream reference docs copied for context.

## Open Defects

- None carried — see `review-apparatus`'s own epic.md for open defects on the live queue.

## Watches

- None.
