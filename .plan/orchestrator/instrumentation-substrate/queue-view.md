<!-- GENERATED FILE — never hand-edit. Rendered from this epic's ledger (status.json, resume_anchor.md, queue/*.json) by `orchestrator regenerate-view --slug instrumentation-substrate`. On a merge conflict in this file, do not merge it by hand: merge the source files, run `orchestrator regenerate-view --slug instrumentation-substrate`, and `git add` the result. -->

# Queue view: Next Level: measured instruction substrate

## START HERE

**Resume anchor**: 2026-09-26 CLEANUP after PM-MCP parking: 0 applied; A1 re-grounding + A5 declined for all 9 (parked/superseded — re-ground only on an operator un-park); no duplicate work (source_origin 0); compact ok (view unchanged); archive_drain=refused; restart_verdict=NOT_READY (225 uncommitted paths repo-wide). NEXT ACTION: operator commits the ledger edits here + the carry-over in plan-marshall-mcp, then `/plan-orchestrator close slug=instrumentation-substrate` unless a row will be un-parked.

2026-09-26 PM-MCP SUPERSESSION (review-apparatus-001 drained): THE WHOLE QUEUE IS PARKED — PLAN-01..08 staged->parked, PLAN-09 already parked; every spec carries a SUPERSEDED BY PM-MCP banner. Carry-over filed at /Users/oliver/git/plan-marshall-mcp/doc/known-defects/instrumentation-substrate-carry-over.md (117 rows, 81 carried, 50 gap; 1 contradiction PM-MIG-5) — UNCOMMITTED in plan-marshall-mcp, the operator commits it. Emission exceptions: none. No emitted-but-unlaunched command existed, so nothing was voided; the older NEXT ACTION below ('/plan-orchestrator next') is VOID — nothing is emittable. other-approaches-001 discarded here, carried to PM-MCP. Inbox empty (live 0, invalid 0). NEXT ACTION: operator commits the carry-over in plan-marshall-mcp and the ledger edits here; then decide whether to `close` this epic (no row is expected to un-park).

--- prior anchor (kept) ---
CLEANUP done 2026-09-22: 9 specs re-grounded at HEAD 7d82d5d90 (38 claims: 23 corroborated, 11 contradicted+rescoped in-place, 4 downgraded to spec-internal reasoning for dead inbox citations). Highest-priority re-scope: PLAN-01's leaf-isolation hypothesis is refuted (harness re-supplies CLAUDE.md into dispatched leaves) — spec now splits attribution-isolated vs realistic-context compliance; this gates WS-01. PLAN-02/PLAN-08 share a widened hard-rule population (CLAUDE.md + persona-plan-marshall-agent + tool-usage-patterns.md) — reconcile at outline, do not derive twice. PLAN-05's 4 of 6 numeric figures were corrected in place. PLAN-09's corrections routed to post-run-quality (owns live PLAN-PRQ-05 successor). Ledger compacted (epic_changed=true, ordered-queue regenerated for PLAN-01's narrowed surface). archive_drain=refused (standing, no epic-wide quiescence signal). restart_verdict=NOT_READY — 83 uncommitted paths at HEAD (this session's spec/ledger edits); commit is an operator decision, not auto-applied. NEXT ACTION: review + commit the cleanup edits, then /plan-orchestrator next slug=instrumentation-substrate.
**Phase**: orchestrating
**Parked**:
- PLAN-01 (WS-01)
- PLAN-02 (WS-01)
- PLAN-03 (WS-02)
- PLAN-04 (WS-02)
- PLAN-05 (WS-03)
- PLAN-06 (WS-03)
- PLAN-07 (WS-04)
- PLAN-08 (WS-01)
- PLAN-09 (WS-05)
**Queue** (staged, in order):
- (empty)

## Ordered Queue

| # | Plan | Workstream | Status | Surface (expected) |
|---|------|------------|--------|--------------------|
| 1 | PLAN-01 | WS-01 | parked | marketplace/bundles/pm-plugin-development/skills/instruction-conformance/; test/pm-plugin-development/instruction-conformance/ |
| 2 | PLAN-02 | WS-01 | parked | marketplace/bundles/pm-plugin-development/skills/instruction-conformance/; test/pm-plugin-development/instruction-conformance/ |
| 3 | PLAN-03 | WS-02 | parked | doc/adr/; doc/developer/marketplace-build.adoc |
| 4 | PLAN-04 | WS-02 | parked | doc/developer/; marketplace/bundles/plan-marshall/skills/eval-cross-model/; test/plan-marshall/eval-cross-model/ |
| 5 | PLAN-05 | WS-03 | parked | marketplace/bundles/; marketplace/bundles/pm-plugin-development/skills/plugin-architecture/references/frontmatter-standards.md; marketplace/bundles/pm-plugin-development/skills/plugin-doctor/; test/pm-plugin-development/plugin-doctor/ |
| 6 | PLAN-06 | WS-03 | parked | marketplace/bundles/plan-marshall/skills/manage-status/; marketplace/bundles/plan-marshall/skills/platform-runtime/; test/plan-marshall/platform-runtime/ |
| 7 | PLAN-07 | WS-04 | parked | marketplace/bundles/plan-marshall/skills/persona-module-tester/; marketplace/bundles/pm-dev-python/skills/pytest-testing/; pyproject.toml; test/pm-dev-python/ |
| 8 | PLAN-08 | WS-01 | parked | CLAUDE.md; marketplace/bundles/plan-marshall/skills/platform-runtime/; test/plan-marshall/platform-runtime/ |
| 9 | PLAN-09 | WS-05 | parked | marketplace/bundles/plan-marshall/skills/manage-lessons/; test/plan-marshall/manage-lessons/ |
