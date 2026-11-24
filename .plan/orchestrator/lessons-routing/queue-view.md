<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: R52 (2026-11-24) DRAINED THE INBOX, 123 messages (Linux, ledger worktree rebased onto main first). Filed to live-blockers: lessons-routing-096 (finalize commit sanction, high), -097 (merge gate vs optional bot, high), -098 (pre-push-quality-gate done on a red build, high), -099 (pm-dev-java S1130/S4144/S6539, domain content), -100 (script-surface recurrence of -044, high). Staged on the operator's word: PLAN-LR-08 (forward framework-owned lessons) and PLAN-LR-09 (route landing leftovers by a standing rule). Archived 103: stale 4, medium 25, low 18, covered 56. Operator graded -096/-097/-098 high; libraries-initial-implementation-048 left medium. OPEN: (1) the five filings and the ledger are NOT landed, land before any other machine drains (Multi-Machine rules 3, 4); (2) PLAN-LR-08/09 declare Skills none, run corpus spec-skills before either is emitted; PLAN-LR-09 owes an Inbound Routing check at outline; both overlap analyze.md and orchestrator.py and the parked LR-02/03, so serialise; (3) pm-mcp-core-m2-m4-v2-034 vs libraries-initial-implementation-075: review-gate picture-heading read reported on 0.1.2184 though fixtures shipped, reproduce against -089; (4) manage-logging decision printed no TOON on this session's first call though it wrote (libraries-initial-implementation-075 item 5, archived medium). Queue: PLAN-LR-01..05 parked, LR-06 retired, LR-07 shipped, LR-08 and LR-09 staged. Next: land, then confirm live-blockers drains -096..-100.
**Phase**: orchestrating
**Parked**:
- PLAN-LR-01 (WS-01)
- PLAN-LR-02 (WS-01)
- PLAN-LR-03 (WS-02)
- PLAN-LR-04 (WS-04)
- PLAN-LR-05 (WS-01)
**Queue** (staged, in order):
1. PLAN-LR-08 (WS-01)
2. PLAN-LR-09 (WS-01)
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
| 6 | PLAN-LR-08 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/**; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/_orchestrator_inbox.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/standards/inbox-envelope.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/lessons-handling.md; test/plan-marshall/manage-lessons/**; test/plan-marshall/plan-orchestrator/** | plan-marshall |
| 7 | PLAN-LR-09 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-status/scripts/_orchestrator_ledger.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/SKILL.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py; marketplace/bundles/plan-marshall/skills/plan-orchestrator/templates/plan-spec.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/analyze.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/handle-open.md; marketplace/bundles/plan-marshall/skills/plan-orchestrator/workflow/orchestrate.md; test/plan-marshall/plan-orchestrator/** | plan-marshall |
