# Landing Analysis: PLAN-03 — marshalld interaction audit logging

epic: plan-server
workstream: WS-01
pr: #949 (squash-merged to main, 2026-07-20)

> Landing record for one shipped plan. Lives at `landings/PLAN-03.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact.

## Ground-truth verification

- PR #949 merged: **corroborated** — `origin/main` carries `aafcd1928 feat(build-server): add client+server interaction audit logging (#949)` (single squash commit via merge queue).
- Changed surface matches spec: **corroborated** — `git show --stat` touches the client (`build-server-client/scripts/build_server.py` +102), the server (`manage-build-server/scripts/marshalld.py` +99 and a NEW `_marshalld_audit.py` +282), the read verb (`manage_build_server.py` +94), correlation + audit tests (`test_interaction_audit_correlation.py` +218, `test_marshalld_audit.py` +343), and both SKILL.md docs. 17 files, +1514/−26. The three loop-back tail-fixes are visible in the diff (pytest-timeout in `pyproject.toml`, guards in `_marshalld_audit.py`).
- Archived plan present: **corroborated** — `.plan/local/archived-plans/2026-07-20-marshalld-interaction-audit-logging/` exists with full artifacts (execution.toon, metrics.md, solution_outline.md, status.json).
- CodeRabbit findings (loop-backs #2 and #3): third-party text in the paste — recorded here as **dispositions only** (fixed + regression-tested per the narrative and corroborated by the diff's guard additions), not acted upon.

## Deliverable Fidelity vs Spec

Spec: `plans/PLAN-03-interaction-audit-logging.md` (5 deliverables).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 Client-side interaction logging | shipped-as-specified | `build_server.py` (+102): submit/enqueue with result, each status query, fallback/refused outcomes → plan work log via manage-logging; CWE-117 control-char sanitization on notation + job_id |
| D2 Server-side interaction audit log | shipped-as-specified | new `_marshalld_audit.py` (+282): central append-only `interaction-audit.log`, per-request attribution (project_root/plan_id/job_id/timestamp/outcome), 7-day GC, secret-key rejection, best-effort guards that never abort request handling. Central-vs-project-specific design question settled toward CENTRAL. |
| D3 End-to-end correlation | shipped-as-specified | `test_interaction_audit_correlation.py` (+218): one job_id traceable client↔server↔change-ledger (kind=job) |
| D4 Audit read affordance + retention | shipped-as-specified | `manage_build_server.py` (+94) `logs` verb, project-scoped + fail-closed; 7-day GC in the audit module |
| D5 Tests | shipped-as-specified | `test_marshalld_audit.py` (+343) + the correlation test + client-side test additions |

Verdict: **5/5 shipped as specified.** No deliverable dropped or substituted. Plus the CAPTURED-LEVEL fallback/refusal logging that the API-Sheriff cross-project datapoint sharpened into a hard requirement (D1) is present — closing the observability gap that made the inert daemon look armed.

## Metrics and Anomalies

- Tokens: 2.5M total.
- Duration: 2h7m worked / 26h53m wall (all 6 phases).
- Anomalies: **three real loop-backs**, all genuine, none in the feature itself:
  1. CI hang — two pre-existing test time-bombs surfaced: a py3.12-only `asyncio.run` subprocess-cancel hang in the correlation test, and a wall-clock `poll_until` busy-loop in re-review tests. Fixed with a pytest-timeout backstop + capped floated tool-env. Lesson 2026-07-20-20-001.
  2. Review loop-back (287b13dd4) — 3 CodeRabbit findings: job_id log-injection, attribution OSError guard, gc round-trip test.
  3. Barrier loop-back (0e4a72917) — the pre-merge comment barrier caught CodeRabbit's review OF loop-back #2, flagging 2 further valid issues (unguarded startup gc(), error-key detail loss). Both fixed + regression test.
  Each loop-back re-verified whole-tree green, re-ran CI, and Sonar re-confirmed 0 new-code issues at the settled HEAD. The barrier catching a review-of-a-review (loop-back #3) is the completion-aware pre-merge barrier working exactly as designed.

## Routing and Merge Behavior

- Review: CodeRabbit active and productive (5 valid findings across two loop-backs, all fixed). No gemini noise this run.
- CI/merge: squash-merged via platform merge queue; CI green at every settled HEAD; Sonar 0 new-code issues each time. #952 (merge-queue-coexistence) landed adjacent on main — disjoint enough that no collision was reported.
- Post-merge tail: cache regenerated to 0.1.1163, 10 bundles synced, on-main executor regenerated (140 scripts) — this cleared the operator-owed executor-regen/bump that the roadmap had outstanding.

## Reconciliation Actions

- [x] status.json `plans[]` PLAN-03 → status `shipped`, pr `#949`, landing `landings/PLAN-03.md`
- [x] epic.md Ordered Queue row reconciled from status.json
- [x] **Worktree-container routing watch — KEPT ACTIVE and re-pointed.** PLAN-03 was slated as the proof point, but ground truth refutes that: no `~/.plan-marshall/marshalld/interaction-audit.log` exists, and the pre-existing job-logs are old-daemon runs that errored (missing-command usage errors). The daemon was stopped for the merge-queue-coexistence finalize (operator-owed restart), so PLAN-03's own builds never routed through the new code. The watch now depends on the daemon being restarted running the #949 code, and re-points to PLAN-04's run.
- [x] resume_anchor updated → emit PLAN-04
- [x] START-HERE block regenerated

## Follow-Ups

- **Worktree-routing proof re-pointed to PLAN-04.** Now doubly gated: the daemon must be (a) restarted and (b) running the post-#949 code that writes `interaction-audit.log`. Settling check once both hold: an `interaction-audit.log` entry whose `project_root`/exec path sits under `.plan/local/worktrees/`. Until then, worktree-container routing remains UNOBSERVED.
- **PLAN-03 itself surfaces the observability tooling** to close the watch: the new central `interaction-audit.log` + the `manage-build-server logs` verb are exactly how future routing gets proven. The watch is now *checkable*, where before it was invisible.
- **Deferred, captured, out of scope (lesson 2026-07-20-20-002):** `plan_logging.log_entry` does not validate a client-supplied `plan_id` — a pre-existing shared-logging gap. Not a plan-server defect; flagged for a dedicated hardening plan in the shared-logging surface, NOT folded here.
- Operator-owed marshalld restart (tracked as an OWED defect in epic.md) is now ALSO the precondition for the worktree-routing proof — clearing it does double duty.
