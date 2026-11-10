<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: R44 (2026-11-10) INBOX DRAINED, TOKENSHERIFF GATHERED, LOCAL CORPUS INGESTED. Inbox (eleventh ingest run): 33 messages, 3 filed high to live-blockers as lessons-routing-084 and -085. Gather (second run): TokenSheriff 22 plan-marshall lessons moved into lessons-archive, 9 project-only stay; API-Sheriff 10 untouched. Ingest (twelfth run): 29 local lessons, 1 filed high as lessons-routing-086 (raw build-server submit builds the wrong tree), 16 stale, 4 medium, 4 already-covered, 4 low archived, corpus 0. Details: epic.md Lesson Sweeps and lessons-archive/INDEX.md Sweep 2026-11-10 (three sections). OPEN: (1) ids the 2026-11-02 second run recorded as left in place (pm-mcp-core 49, API 25, nifi 6) are not on this machine, likely a different machine, not verified; (2) R41 filings 075..083 sit in live-blockers inbox/archive/lessons-routing, whether dispositioned is not established; (3) live-blockers inbox now holds undrained filings 084, 085, 086 from this epic. Queue unchanged: PLAN-LR-01..05 parked, nothing emittable. Next: land the shared ledger worktree (this session runs it); then confirm live-blockers drains 084..086.
**Phase**: orchestrating
**Parked**:
- PLAN-LR-01 (WS-01)
- PLAN-LR-02 (WS-01)
- PLAN-LR-03 (WS-02)
- PLAN-LR-04 (WS-04)
- PLAN-LR-05 (WS-01)
**Queue** (staged, in order):
- (empty)
- PLAN-LR-06 (WS-05) — status: retired
- PLAN-LR-07 (WS-01) — plan=plan-lr-07-lessons-verb-routing — PR 1584 — landing=landings/PLAN-LR-07.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) | Lane |
|---|------|------------|--------|--------------------|------|
| 1 | PLAN-LR-01 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-lessons/** | plan-marshall |
| 2 | PLAN-LR-02 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; test/plan-marshall/manage-lessons/** | plan-marshall |
| 3 | PLAN-LR-03 | WS-02 | parked | marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; test/plan-marshall/manage-lessons/** | plan-marshall |
| 4 | PLAN-LR-04 | WS-04 | parked | (prose) | plan-marshall |
| 5 | PLAN-LR-05 | WS-01 | parked | marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; test/plan-marshall/manage-lessons/** | plan-marshall |
