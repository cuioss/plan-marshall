<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug lessons-routing`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug lessons-routing`, and `git add` the result. -->

# Queue view: Lessons Routing

## START HERE

**Resume anchor**: === R25 (2026-09-27) CLEANUP. Ledger reconciled (7/7), settled narrative relocated, epic kept open by operator. Nothing to emit: queue fully parked (PM-MCP), lessons corpus 0. Next: commit+land this ledger via PR; next `lessons` run routes new lessons to the PM-MCP carry-over, not sibling inboxes. === === R24 (2026-09-27). DONE: #1636 merged (075ffbb68) with the legacy fixes + ledger. All 43 swept lessons retired (tombstoned); corpus now 0 active. Queue: PLAN-LR-01..05 parked (PM-MCP). Only open item: operator decision (d) close this epic; PM-MCP carry-over file awaits operator commit in plan-marshall-mcp. === === R23 (2026-09-26). Decision (b) done: legacy-blocking fixes in PR #1637 (branch fix/legacy-delivery-false-blocks) - self-review stale base, foreign_pr_gate plan branch, rebase-to ancestry noop; 23-23-001 re-verified stale. OPEN: (a)+(c) lesson retirement (37 + unreadable 2026-09-22-12-001) blocked by auto-mode permission on manage-lessons remove - operator action. After #1637 merges, the 4 legacy-blocking lessons (24-09-003, 24-12-006, 24-12-001, 24-05-001) and 23-23-001 are retireable too. Note: another session's commit cc127260b landed this epic's R22 ledger edits on local branch fix/legacy-delivery-blockers. === === R22 (2026-09-26). PM-MCP SUPERSESSION. Drained review-apparatus-001 (archived). PLAN-LR-01..05 PARKED (bannered SUPERSEDED BY PM-MCP, Do NOT emit; un-park only by operator). No emitted-but-not-launched command existed - nothing voided. Lessons sweep (43): 36 superseded-by-pm-mcp, 5 legacy-blocking, 1 stale, 1 unreadable; clusters went to the PM-MCP carry-over, NOT to sibling inboxes (clusters_routed 0). Carry-over filed UNCOMMITTED at /Users/oliver/git/plan-marshall-mcp/doc/known-defects/lessons-routing-carry-over.md - operator commits it. NEXT: operator decisions (a) retire the 37 superseded+stale lessons from the corpus, (b) legacy-fix or accept the 5 legacy-blocking lessons (24-09-003+24-12-006 self-review stale base, 24-12-001 foreign_pr_gate, 24-05-001 sync-baseline rebase, 23-23-001 ruff isort), (c) unreadable 2026-09-22-12-001, (d) close this epic. Then commit the lessons-routing tree. R21 below still stands (uncommitted-paths blocker). === === R21 (2026-09-24). Drained the one remaining inbox message, api-sheriff-deployment-configurability-004.md (a new PLAN-29/PR#348 finding, not R19's already-forwarded set). Not lessons-routing's own subject; discarded here and split-forwarded via inbox write --kind finding: items 1+2 (argparse/flag-shape recurrence incl. qgate list missing --phase) to process-compliance as lessons-routing-003.md; item 3 (ci_wait adaptive-timeout budget mismatch, a confident-signal-hides-a-caveat pattern - 5 identical 'accepted' triage verdicts masking a real capacity gap) to truthful-signals as lessons-routing-002.md. Inbox now Empty (live_count:0, no closed_senders). This closes out R20's first restart-readiness blocker. Second blocker (14 uncommitted worktree paths) still open - next action: branch+commit+PR+merge-queue+pull the accumulated settled.md relocation and layout-migration changes. READ R1-R21. === R1-R19: unchanged, see prior anchor text in settled.md/epic.md Decisions history and logs/decision.log. R20: cleanup pass - relocated closed 2026-09-22 sweep record to settled.md; A1-A4 clean, no verdict changes; restart_verdict was NOT_READY on the two blockers named above.
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
