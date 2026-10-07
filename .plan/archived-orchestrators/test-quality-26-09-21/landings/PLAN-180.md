# Landing Analysis: PLAN-180 — Test Fidelity Rules

epic: test-quality
workstream: WS-01
pr: #1538 (carve-1, D5) + #1549 (carves 2–4, all remaining deliverables)

> Landing record for one shipped plan. Lives at `landings/PLAN-180.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

PLAN-180 shipped in two carves under one queue row: carve-1 (D5) as #1538
(`cd6436a4a`, reconciled earlier as a partial with no ship semantics) and
carves 2–4 (all 8 remaining deliverables) as #1549 (`ada9d8d6`). This record
covers the full ship; the carve-1 partial reconciliation stands as the
in-progress history, not a duplicate landing.

## Deliverable Fidelity vs Spec

Spec: `plans/PLAN-180-test-fidelity-rules.md` (9 deliverable slots D1–D5,
D7–D9; D5 landed first). Realized at `ada9d8d6` (12 files, +955/−9):

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D5 — fixture-yield docstrings (carve-1) | shipped-as-specified | #1538 merged `cd6436a4a`; guard + matched controls + 10 live fixes (prior partial reconciliation) |
| D1 — hoisted base argv | shipped-as-specified | `build.py` wiring + `test_build_execute_routing.py` guard, PR #1549 body names matched negative control |
| D2 — scoped temp-root pruning | shipped-as-specified | `build.py` pruning wiring + `test_build_cmd_coverage.py` (+110) |
| D3 — tool-default footprint test | shipped-as-specified | `doc/developer/build.adoc` (+39) + coverage test |
| D4 — seam-pinned mirrors | shipped-as-specified | `testing-methodology.md` rule (+41) + mirror guard |
| D7 — skills-root patch | shipped-as-specified | fix + rule prose both present per carve-1 outline verdicts; in #1549 tree |
| D8 — single registration | shipped-as-specified | `testing-pytest.md` registration rule + guard |
| D9 — basetemp relocation | shipped-as-specified | `testing-pytest.md` coexistence (+128) + `pyproject.toml` config; `.plan/temp/scratch/` carve-out, suite owns only `.plan/temp/pytest-*` fully enumerated |

Evidence checked: `ci pr view --pr-number 1549` (state `merged`,
merge_commit `ada9d8d6`), `git log` (commit on main under HEAD `1e2aa916a`),
`git show --stat` (12 files above), archived plans
`2026-09-19-test-fidelity-rules` + `2026-09-20-test-fidelity-rules-follow-up`,
test-quality inbox EMPTY (follow-up filed outward only: 10 notes to the
compliance inbox, 2 lessons to the corpus — nothing owed here).

## Metrics and Anomalies

- Tokens: not reported in the finalize paste (no transcript-sourced figure;
  `record-metrics enrich` path uncited) — recorded as UNMEASURED, not zero.
- Tasks: 19 (14 plan + 5 review-bot fixes), all verified green; no new skips.
- Review/loop-backs: 1 review-bot fix round, 1 self-review loop-back, 1
  stale-merge-queue prune — all closed. Blocking-finding gate clean (1 filed
  bug evidenced fixed).
- Anomalies (all operator-overridden and logged by the plan): `uv.lock` dirt
  ignored; finalize without session identity; **3 wrong `simplify` deletions
  reverted** — they would have gutted deliverable guards (the one legitimate
  stale-count fix kept). The revert is recorded as positive self-correction.
- Hygiene (optional, operator-owned): run `/marshall-steward` (session hook +
  config seed refresh); prune the 10 compliance-inbox notes once read.

## Routing and Merge Behavior

- Review: CodeRabbit + Sourcery per PR body release notes; 5 review-bot fixes
  folded via TASKs. Merge via platform merge queue (squash) at `ada9d8d6`.
- No rebase collisions (N=1 sequential, flight line empty at both carves).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-180 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-180 --field pr --value #1538, #1549` (carve-1 + follow-up; multi-PR precedent: PLAN-010, PLAN-130)
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-180 --field landing --value landings/PLAN-180.md`
- [x] row `plan_marshall_plan_id` already `test-fidelity-rules` (stamped at carve-1 drain; follow-up ran under the same row by operator direction)
- [x] epic.md queue reconciled from status.json
- [x] declaration-form measurement recorded (tenth): ~9 of 12 realized files outside the 2 declared directories — see Follow-Ups
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary`

## Follow-Ups

- **DECLARATION FORM — severe under-declaration, second instance in this
  direction.** Declared: 2 directories (`persona-module-tester/`,
  `pytest-testing/`). Realized: 12 files, of which only the two standards files
  sit inside the declaration — `build.py`, `pyproject.toml`,
  `doc/developer/build.adoc`, `test/_shared/_test_shape_scan.py`,
  `test/conftest.py`, 4 `test/plan-marshall/*` guards and
  `test/test_harness_shape_guards.py` (9 files) land outside it. Mechanism is
  named: D9's basetemp relocation and the build wiring necessarily touch
  production-adjacent files a test-fidelity spec does not naturally declare —
  the same will-read/will-modify conflation plus a third relation
  (will-WIRE-through). No pairing misled (N=1, flight empty). → carried as
  evidence for the declaration-form question, no new plan.
- **PLAN-180's open HYPOTHESIS now settles:** the claim "CLI-validated argv
  constants plus scoped pruning plus seam-pinned mirrors hold the suite
  honest" corroborated by this landing — stamp `corroborated` via
  `corpus set-verdict` (done alongside this reconciliation).
- **Epic close candidacy re-opens:** PLAN-180 shipped leaves only PLAN-140
  (`parked`) non-terminal. Close still needs the operator's PLAN-140
  disposition — see the close assessment.
