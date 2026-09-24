<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: === R20 (2026-09-24). cleanup pass under the new per-concern layout: A1 re-grounding found zero HEAD-drift for LR-01..05 (5 intervening commits touched unrelated surfaces) - all prior verdicts stand, nothing re-persisted. corpus surfaces unchanged (LR-04 stays prose/indeterminate, deliberate per prior cleanup). A4 duplication clean for the 5 staged specs; PLAN-LR-07 (shipped) shows expected shared-doc overlap with truthful-signals on orchestration-model.md/SKILL.md/lessons-handling.md - not actionable, already shipped. Phase B: relocated the closed 2026-09-22 sweep record out of epic.md's '## Lesson Sweeps' section into new settled.md (operator-confirmed via AskUserQuestion), pointer left in place, compact invariants ok. Phase C: archive_drain refused per standing contract (no epic-wide quiescence signal). Phase D restart_verdict: NOT_READY - two blockers: (1) inbox/api-sheriff-deployment-configurability-004.md still unconsumed (a straggler from the prior 'drain and distribute' pass - draft relay to process-compliance exists in scratchpad but was never filed via inbox write/archive before the session summary interrupted it - needs re-draining as a follow-up, NOT part of cleanup); (2) 14 uncommitted worktree paths at 9588b30b3 (the settled.md relocation plus prior unmigrated changes - needs a commit/PR cycle). Next action: drain the one remaining inbox message (kind=finding, route to process-compliance per its WS-07-finalize-mechanism fit), then commit+branch+PR the accumulated changes. PLAN-LR-01 emission still blocked on the marketplace-wide corpus_comparison_determinate:false (94 indeterminate sibling specs, unrelated to this epic - see R17). READ R1-R20. === R1-R19: unchanged, see prior anchor text in epic.md's Decisions/Lesson-Sweeps history (now settled.md) and logs/decision.log.
**Phase**: orchestrating
**Queue** (staged, in order):
1. PLAN-LR-01 (WS-01)
2. PLAN-LR-02 (WS-01)
3. PLAN-LR-03 (WS-02)
4. PLAN-LR-04 (WS-04)
5. PLAN-LR-05 (WS-01)
- PLAN-LR-06 (WS-05) — status: retired
- PLAN-LR-07 (WS-01) — plan=plan-lr-07-lessons-verb-routing — PR 1584 — landing=landings/PLAN-LR-07.md — status: shipped

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-LR-01 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/** |
| 2 | PLAN-LR-02 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; test/plan-marshall/manage-lessons/** |
| 3 | PLAN-LR-03 | WS-02 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; marketplace/bundles/plan-marshall/skills/tools-integration-ci/**; test/plan-marshall/manage-lessons/** |
| 4 | PLAN-LR-04 | WS-04 | staged | (prose) |
| 5 | PLAN-LR-05 | WS-01 | staged | marketplace/bundles/plan-marshall/skills/manage-lessons/SKILL.md; marketplace/bundles/plan-marshall/skills/manage-lessons/scripts/**; test/plan-marshall/manage-lessons/** |
