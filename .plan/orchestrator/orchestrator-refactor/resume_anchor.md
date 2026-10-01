2026-10-01 — PLAN-11 RUNNING (plan cross-check-dated-archive-self-collision, operator-confirmed start, emitted on operator override of the indeterminate gate). It carries the folded D4: explicitly exclude the NO_PLAN plan-less sentinel from cross-check's live_plan candidates (operator-reported from a consumer project, corroborated at 391efbbd6); 5 deliverables, surface 7; claim-3 verdict corrected to rescoped=yes. Next action: wait for PLAN-11's landing message in inbox/, then analyze. Do NOT re-scope its spec while running. PLAN-10 stays staged behind it (shared orchestrator.py) and still overlaps live plans — re-check at next. Parked, do NOT emit: PLAN-03/05/06/07. Open operator questions: per-candidate vs whole-population fail-closed scope (Open Defect 2026-09-22); whether live plan antigravity (1-init since 2026-09-17) is abandoned. PLAN-09 lesson rows kept at findings/2026-09-28-plan-09-lesson-carry-over.md until the operator introduces a target — then move them and retire that file.

2026-09-29 — CLEANUP DONE, restart-ready (PLAN-10 re-grounded + re-scoped at fa7b51774, surface 14 entries).

2026-09-28 — PLAN-09 SHIPPED (#1652, 438a0a71f). #1641's revert of this tree restored from 88fcfc9ef and landed (#1656); record relocated to settled.md.

2026-09-26 — QUEUE PARKED, PM-MCP SUPERSEDES IT (review-apparatus-001 drained); PLAN-09/10/11 later re-staged by operator decision.

PREVIOUS ANCHOR (kept): Cleanup pass shipped (PR #1621, merge 54b4bb525): 30 A1 verdicts re-grounded, PLAN-10/PLAN-11 re-scoped. restart-check: ready.
