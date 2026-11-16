<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: R51 (2026-11-16) GATHERED API-SHERIFF AND TOKENSHERIFF (third gather run, Linux machine). Probed eleven sibling checkouts: stores API-Sheriff 10 and TokenSheriff 49, all others zero. 59 lessons graded; 31 plan-marshall lessons moved into lessons-archive (12 filed, 4 medium, 1 stale, 14 low or already covered); 28 project-only stay in their checkouts. Filed to live-blockers, all operator-graded: lessons-routing-092 (dispatch seam answers prompt_not_found for installed level-N agents, reproduced), -093 (root aggregator module-tests is plain mvn test against a sibling test-jar), -094 (the marker-detect gate has no caller), -095 (one umbrella of six domain-content gaps). The run started on a ledger worktree 42 commits behind main, which broke the Multi-Machine Operation ruling (fetch main and replay first): the four filings were first numbered -087..-090 and collided with the filings already on main (-087..-091), so the land was rebased onto main and the four renumbered to -092..-095. Details: epic.md Lesson Sweeps 2026-11-16 and lessons-archive/INDEX.md Sweep 2026-11-16. OPEN: (1) live-blockers inbox holds undrained filings 087..095; (2) -093 rests on a code reading, Maven was not run; (3) R50 items still stand: sh-004 and sh-005 graded medium on Linux and high on macOS (the later one is filed, operator may confirm); PLAN-LB-129 is running and may own part of -089; R41 filings 075..083 disposition in live-blockers inbox/archive not established; whether PLAN-LB-46 covers the CodeRabbit full-review fallback notice not checked; sh-002 item 3 and sh-005 versus #1992 not verified, archived medium; pm-mcp-core 2026-10-12-13-006 is medium if read as a phase-3-outline gap; the third machine is not named anywhere in the ledger. Queue unchanged: PLAN-LR-01..05 parked, nothing emittable. Next: confirm the land merged, then live-blockers drains 087..095; every session fetches main and replays the ledger worktree before any writing verb.
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
