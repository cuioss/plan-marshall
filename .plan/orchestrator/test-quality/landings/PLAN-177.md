# Landing Analysis: PLAN-177 — Close the Leftover Gate Gaps

epic: test-quality
workstream: WS-03
pr: #1534 (merged as a5977d953d49b0868721095a97018eaa55f50797)

> Landing record for one shipped plan. Lives at `landings/PLAN-177.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

## Deliverable Fidelity vs Spec

Spec: `plans/PLAN-177-close-the-leftover-gate-gaps.md` (D1 rule fix, D2 isolation
discrimination test). Realized footprint at `a5977d953` (6 files, +591/−32):

- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/scripts/_analyze_test_conventions.py`
- `marketplace/bundles/pm-plugin-development/skills/plugin-doctor/standards/doctor-test-conventions.md`
- `test/pm-plugin-development/plugin-doctor/fixtures/test_conventions/rule2/README.md`
- `test/pm-plugin-development/plugin-doctor/test_test_conventions_rule2.py`
- `test/sync-plugin-cache/test_staleness_guard.py`
- `test/test_runner_falsifiability.py`

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — Fix the rule's five false-positive shapes (462a76, c0f4ef, 02c9ea, 79bf95, 24970a), matched clean/violation control pairs, gate green | shipped-as-specified | `ci pr view --pr-number 1534`: state `merged`, merge_commit `a5977d953`; `git log --oneline`: `a5977d953` on main under HEAD `5feeff9429`; diff extends Rule 2 detector (+286 analyzer lines) with scrub/helper/`-m` exemptions, `test_test_conventions_rule2.py` +249 with matched control pairs, fixtures README +13; 3 CodeRabbit actionable inline findings remediated in-run via TASK-4/TASK-005 follow-up commits (threads resolved, `Addressed in commit aa6d4c7`) |
| D2 — Discriminate the `_run_python` isolation (fail on old regime, pass on new; existing consumers still pass) | shipped-as-specified | `test/sync-plugin-cache/test_staleness_guard.py` +28 (isolation regression test), `test/test_runner_falsifiability.py` +38 (falsifiability guard for the new shapes); `landing-facts`: `deliverables_total=2 deliverables_done=2` |

Added-unplanned (in-run repairs, no spec change owed): Q-gate contract-drift fix
(doc commit `b8cce0470` qualifying Class-3 as py_compile-only, per inbox
`close-the-leftover-gate-gaps-004.md`); doc exemption parity fix (`a2e5a0`).

Declaration note (not a blocker): the realized footprint exceeds the spec's three
`## Expected Surface` HYPOTHESIS entries by two files —
`.../plugin-doctor/standards/doctor-test-conventions.md` and
`test/test_runner_falsifiability.py`. Both are adjacent to declared surfaces (the
doc the narrowed exemption had to keep in parity, the harness guarding the new
test shapes). No pairing decision was misled (N=1 sequential, flight line empty);
no surface correction is owed post-ship.

## Metrics and Anomalies

- Tokens: `total_tokens=0` — `record-metrics enrich` skipped without session identity per operator override (proceed unenriched); no transcript-sourced session tokens. Non-blocking by override.
- Duration: `total_wall_seconds=77135.0` (~21h25m, matches operator paste).
- Anomalies: `create-pr` recorded `pr_number=1531`, but #1531 closed unmerged and the branch was re-proposed as #1534 (merge-queue merged) — corroborated via `ci pr view` (#1531 `closed`, `merge_commit_sha: null`; #1534 `merged`). `landing-facts.steps` carries `emit-landing:pending, archive-plan:pending` (block captured mid-finalize; both done per operator paste). `uv.lock` dirtied by `./pw generate-claude` (ruff 0.16.6→0.16.8) — revert if unwanted. Phase-gates plan's uncommitted changes preserved via stash/pop (6 modified + 1 untracked at analyze time).

## Routing and Merge Behavior

- Review: CodeRabbit 3 actionable inline findings (env-binding scope/reachability `02ad26`, `-m` launcher restriction `9d0ea1`, scrub key-vs-value `260429`) + review_body doc-parity note (`a2e5a0`) — all remediated in-run (TASK-4/TASK-005, `aa6d4c7`); Sourcery APPROVED (`2026-09-19T06:51:52Z`) after an earlier rate-limit notice; 9 comments unresolved at analyze time, of which 1 is a post-merge-round actionable lead (see Follow-Ups).
- CI/merge: merge-queue merge (`a5977d953`), `merge_state=merged`, `cleanup_owed=false`; branch `feature/close-the-leftover-gate-gaps` gone (`git branch -a` clean), plan archived at `.plan/local/archived-plans/2026-09-19-close-the-leftover-gate-gaps` (`phase_closure: complete`). No rebase collisions (N=1, no live pair).
- Inbox: `inbox landing-check` on `close-the-leftover-gate-gaps-008.md` → `complete: true`, `missing_keys[]` empty. 7 `candidate-lesson` + 1 `landing` queued from this sender plus 1 `finding` from `module-budget-campaign-run-2-slice-040` — left queued for the inbox-scan drain (this paste-mode analyze reconciles the ship only).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-177 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-177 --field pr --value #1534`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-177 --field landing --value landings/PLAN-177.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-177 --field plan_marshall_plan_id --value close-the-leftover-gate-gaps`
- [x] claim verdict persisted — `corpus set-verdict --plan PLAN-177 --claim-index 1 --verdict corroborated` (the dispatch-time HYPOTHESIS on the five instances/shapes held; fixed as briefed, narrowed to py_compile-only per review)
- [x] epic.md queue reconciled from status.json
- [x] Open Defect added (post-merge review lead `_has_pythonpath_env_kwarg` name-only shortcut); Watch added (realized-vs-declared delta class, already absorbed here)
- [x] resume_anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] START-HERE and Ordered Queue blocks regenerated — `orchestrator resume-summary` (one invocation emits both; no `(!) missing:` marker — `pr` and `landing` stamped)

## Follow-Ups

- Open Defect (from the latest CodeRabbit round, posted `2026-09-19T06:55:51Z`, unresolved): `_has_pythonpath_env_kwarg` accepts `env`/`subprocess_env`/`child_env` names before calling `_resolve_env_binding`, so `env = {}` + `env=env` reads as safe despite no `PYTHONPATH`. Fix: remove the name-only shortcut or require the resolved binding to match a trusted shape. → WS-03, unowned (PLAN-177 shipped; fold into the next instrument-hardening plan or stage on demand).
- Inbox drain owed: `analyze slug=test-quality` with no paste drains 9 queued messages (7 candidate-lessons 001–007 incl. the OUTCOME/dispatch-boundary/argparse process trio, 1 landing 008 already reconciled here, 1 slice-040 finding 005). Candidate-lesson dispositions (promote/fold/stage/discard) belong to that drain, not to this ship reconciliation.
- Run 3 (slice 060) staging stays just-in-time per the prior anchor; PLAN-180 (`test-fidelity-rules`, WS-01) is the staged candidate — see the proactive emit below.
