# Landing Analysis: PLAN-LB-22 — Finalize loop control

epic: live-blockers
workstream: WS-01
pr: #1718 (https://github.com/cuioss/plan-marshall/pull/1718)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-22.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-22-finalize-loop-control-016.md` (kind `landing`, `landing-check`
`complete: true`). Checked against `ci pr queue-state --pr-number 1718` (`pr_state: merged`,
`merge_commit_sha: 6b00815e08a21161acf5f498c31f27c3fda39836`, merge-group run concluded
`success`), against `git show --stat 6b00815e0` (54 files, 5385 insertions, 272 deletions), and
against the diff of `pre-submission-self-review.md` in that commit, which was read in full. The
other 53 files were not read; verdicts on them rest on the file list, the test modules added,
and the PR description.

## Deliverable Fidelity vs Spec

Deliverables are named by their source tag in the spec.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| PLAN-LB-10 D1 — retry and re-fire transitions legal without `--force` | shipped-as-specified | `_cmd_mark_step.py` (+152); new `test_mark_step_done_retry_transitions.py`; the self-review workflow now says "Neither direction of this step's round loop requires `--force`" and names the transition table |
| PLAN-LB-10 D2 — `ci_verify` reports the write | shipped-as-specified | `ci_verify.py` (+94), `test_ci_verify_core.py` (+321), `test_ci_verify_cli.py` |
| PLAN-LB-10 D3 — the dispatcher's own `failed` records are parsed | shipped-as-specified | `phase-6-finalize/SKILL.md` (+148); new `test_dispatcher_failed_mark_result_parse.py` |
| PLAN-LB-10 D4 — contract text and step documents match the tool; population published | shipped-as-specified | `external-step-contract.md`; `adr-propose.md` and `lessons-capture.md` gained the flag where the table needs it; the PR body carries the population (25 step documents, 76 terminal invocations, 7 needing `--force`); new `test_step_terminal_mark_transitions.py` |
| PLAN-LB-02 D1 — a logged verb grants further rounds | shipped-as-specified | new `_cmd_loop_back.py` (534 lines); `test_loop_back_grant.py`, `test_loop_back_admit.py` |
| PLAN-LB-02 D2 — a recorded operator close on named residual findings | shipped-as-specified | `manage-status loop-back close`; the workflow's "out of budget" close names it and records `may_close=operator_override`; `test_loop_back_close.py`, `test_pre_submission_self_review_operator_close.py`. Used on this plan's own finalize |
| PLAN-LB-02 D3 — loop-back budgets are per source | shipped-as-specified | the workflow now reads "the `max_iterations` ceiling is spent per requesting source"; `execution.md` and `execution-recovery.md` changed |
| PLAN-LB-02 D4 — the step's own state findings can resolve | shipped-as-specified | state findings carry `--rule pre-submission-self-review-state`; a closing round resolves them with the new `qgate resolve-by-rule`; `test_qgate_resolve_by_rule.py` |
| PLAN-LB-02 D5 — `verdict_inputs` on simplify and lessons-housekeeping | shipped as the recorded refusal for both | The spec allowed a refusal on evidence, and the re-grounding note of 2026-10-08 predicted it for simplify. Consequence: both steps still re-fire on every HEAD advance (message `-008`) |
| PLAN-LB-05 D5 — a wait lapse on a live CI run is pending, not a finding | shipped-as-specified | `ci_complete_precondition.py` (+154), `ci-verify.md`; `test_ci_complete_precondition_checks.py` (+185) |

Added beyond the ten, at operator request (landing message): the `manage-status` Scripts
table lists the loop-back verbs and `update-field`; a status-guard timeout at the
operator-close waiver stamp returns `close_incomplete`.

Realized surface: the spec declared directories under `phase-6-finalize/` and three test
directories, so most of the 54 files fall inside it. Files outside any declaration:
`doc/user/configuration.adoc`, `manage-config/standards/api-reference.md` and `data-model.md`,
`marshall-steward/references/wizard-flow.md`, `plan-marshall/workflow/triage.md` and
`verification-feedback.md`, `ref-workflow-architecture/standards/findings-pipeline.md`,
`workflow-integration-github/standards/automated-review-lifecycle.md`,
`plugin-doctor/references/rule-catalog.md` with its test, and
`test/plan-marshall/manage-findings/timestamp_render_classification.json`. Three of them are
declared by plans still open: `triage.md` and `verification-feedback.md` by PLAN-LB-24 (running)
and PLAN-LB-26, `findings-pipeline.md` by PLAN-LB-25.

## Metrics and Anomalies

- Tokens: 15,990,411 (landing facts); the plan's retrospective puts finalize at 5.93M of 15.3M.
- Duration: 47,692 seconds wall time (about 13.2 hours).
- Anomalies:
  - `pre-submission-self-review` never converged: four rounds before the PR (5, 4, 2, then 7
    findings on the closing full pass, 324 candidates over 53 files), all prose or contract
    claims, closed by the operator-close verb this plan built. No full-surface pass ran after
    the last pre-PR fix; three post-PR fix commits were reviewed at delta scope only.
  - `lessons-housekeeping` and `plugin-doctor` fired seven times each with identical results;
    a three-file fix commit re-ran every head-dependent step.
  - `scope_creep_check` failed nine times with `finding_persist_failed` and reported 5625
    residual files after a rebase (message `-002`).
  - The freshness check refused every per-bundle build row, so each fix commit owed a
    whole-tree `verify` (message `-007`).
  - The merge lock was released early during branch cleanup (message `-014`).
  - The PR's Intent section was cut at its length budget and lost the non-goals (`-015`).

## Routing and Merge Behavior

- Review: both required bots reviewed and re-reviewed twice. Three substantive comments: two
  fixed, one judged wrong and stored `accepted` (the store has no way to say "the reviewer
  was wrong", message `-011`). CodeRabbit's reply to the re-review trigger was stored as a
  finding twice (`-010`); the numbered re-trigger procedure reached one stale bot of two
  (`-009`). Sourcery refused on diff size.
- CI/merge: squash-merged through the merge queue.
- Collisions with plans in flight: this landing changed `phase-6-finalize/SKILL.md`,
  `automatic-review/SKILL.md`, `triage.md` and `verification-feedback.md`, all declared by
  PLAN-LB-24 (running), and `pre-push-quality-gate`-adjacent standards PLAN-LB-23 (running)
  works beside. Both rebase onto `6b00815e0`.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-22 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-22 --field pr --value 1718`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-22 --field landing --value landings/PLAN-LB-22.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-22 --field plan_marshall_plan_id --value lb-22-finalize-loop-control`
- [x] epic.md narrative reconciled against the queue rows (queue annotations)
- [x] Watches added: PLAN-LB-23 and PLAN-LB-24 rebase onto this landing; head-dependent steps still re-fire on every fix commit
- [x] the held standalone self-review plan reconciled with this landing and released to the operator
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated and committed with the row change

## Follow-Ups

- Messages `-002` and `-004`: folded into PLAN-LB-27 (scope-creep guard recurrence;
  `affected_files` does not grow with fix tasks). No surface added.
- Message `-005`: folded into PLAN-LB-26 (triage `deliverable: 0` recurrence). No surface added.
- Message `-014`: folded into PLAN-LB-25 as its tenth deliverable (merge lock released early);
  two surface entries added.
- Messages `-007`, `-009`, `-010`: recurrences of what PLAN-LB-23 and PLAN-LB-24 fix; both
  plans are running, so they are recorded in `epic.md` Queue annotations and not in the specs.
- Message `-012`: folded into the standalone self-review plan's brief.
- Messages `-003`, `-006`, `-008`, `-011`, `-013`, `-015`: promoted to the lessons corpus as
  `2026-10-08-21-001` to `-006`. None has an owning plan in this epic.
