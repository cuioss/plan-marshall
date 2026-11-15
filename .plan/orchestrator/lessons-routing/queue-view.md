<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: R50 (2026-11-15) MULTI-MACHINE RULING PERSISTED. Operator: this epic runs on three machines and every lessons store is local, so divergence between machines is normal; epic.md now carries the section Multi-Machine Operation (RULING 2026-11-15: a lesson missing on another machine is not lost, every sweep record names its machine, fetch main and replay the ledger worktree before any writing verb, two machines can drain the same inbox message and file the same live-blockers number, two operator rulings can differ, land at the end of every action). That closes the old Unreconciled notes (ids missing across machines; the 25 API-Sheriff lessons on macOS versus 25 Linux tombstones). STATE: PR 1995 (macOS gather re-grade, second grading of 13 inbox messages, live-blockers filings lessons-routing-089..091) MERGED as 930d12b93 and resynced; the Linux session R46-R48 (filings -087, -088) stand beside it. OPEN: (1) sh-004 and sh-005 were graded medium on Linux and high on macOS; the later one is filed, operator may confirm; (2) PLAN-LB-129 is running and may own part of -089; (3) R41 filings 075..083 disposition in live-blockers inbox/archive not established; (4) whether PLAN-LB-46 covers the CodeRabbit full-review fallback notice not checked; (5) sh-002 item 3 (explicit off lane) and sh-005 versus #1992 not verified, archived medium; (6) pm-mcp-core 2026-10-12-13-006 is medium if read as a phase-3-outline gap; (7) the third machine is not named anywhere in the ledger, so its parent path for gather is unknown. Queue unchanged: PLAN-LR-01..05 parked, nothing emittable. Next: the next session on any machine fetches main and replays the ledger worktree first, then ingests its own corpus or gathers its own siblings.
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
