<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: R48 (2026-11-15) DRAIN: 38 inbox messages scanned and archived (a02-079..085, sh-001..005, pm2-008..033), 0 invalid; inbox is EMPTY (a later message is still possible). Filed to live-blockers: lessons-routing-087 (high: a phase-5 gate-rewrite or style commit has no change-ledger row, 5-6 transition refuses; sources pm2-009, -021, -023) and lessons-routing-088 (high, operator: baseline-drift recovery never rebases, so a conflicting drift cannot clear; source pm2-028). Also: 2 already-covered, 2 stale, 24 medium, 6 low, all archived with INDEX.md § Sweep 2026-11-15 (third run). Operator kept the verdict_inputs cluster and the branch-cleanup stall at medium. Earlier this session: R47 ingest (corpus now empty), R46 Linux gather (1 moved, 27 left in source). live-blockers filings 084..086 of 2026-11-10 are archived there, so that item is closed. OPEN: (1) the 25 API-Sheriff lessons missing on macOS: Linux API-Sheriff holds 25 tombstones, same count, ids not compared; (2) R41 filings 075..083 sit in live-blockers inbox/archive/lessons-routing, disposition not established; (3) coverage gap: other-llm-projects and other-test-projects do not exist on this machine; (4) whether PLAN-LB-46 covers the CodeRabbit full-review fallback notice was not checked; (5) sh-002 item 3 (explicit off lane kept under the full posture) and sh-005 versus #1992 were not verified, both archived medium. Queue unchanged: PLAN-LR-01..05 parked, nothing emittable. This session's ledger edits (R46, R47, R48) are unlanded. Next: land the shared ledger worktree (action 6), after checking PR #1956 state.
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
