<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: R39 (2026-11-02) TENTH INGEST RUN, CROSS-REPO (after R38 inbox drain). 5 sibling stores, 178 lessons: 96 moved into lessons-archive (filed 10 / already-covered 33 / medium 18 / low 30 / stale 5), 82 project-only left in source (operator). Filed to live-blockers (undrained): 069 build daemon two builds in one worktree (operator high), 070..074 domain content (pm-dev-java, cui-logging, oci-security, ref-svg-diagrams, jest-testing). Also undrained there from R38: 060 (amended), 064..068. Open: store enumeration was hand-probed (no Glob) - re-sweep with a wildcard listing when available; 2026-11-01 left-in-place ids missing from source unreconciled. Queue unchanged: PLAN-LR-01..05 parked, nothing emittable. Next: (1) land the ledger with /plan-orchestrator land; (2) confirm live-blockers drains 058..074; (3) ingest again on refill.
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
