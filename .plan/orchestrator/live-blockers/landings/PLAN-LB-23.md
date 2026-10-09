# Landing Analysis: PLAN-LB-23 — Verify builds

epic: live-blockers
workstream: WS-02
pr: #1729 (https://github.com/cuioss/plan-marshall/pull/1729)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-23.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-23-verify-builds-014.md` (kind `landing`, `landing-check`
`complete: true`; its surface delta is `unmeasured`, because neither a declared nor a
realized set was supplied to the check). Checked against:

- `ci pr queue-state --pr-number 1729`: `pr_state: merged`,
  `merge_commit_sha: c9738952a80a5020c4ba258c2c9b0dae31a05672`, merge-group run `success`.
- `git show --stat c9738952a`: 56 files, 4629 insertions, 574 deletions.
- A read-only review of the commit against the spec, deliverable by deliverable, by a
  delegated agent that ran nothing and read the hunks and the new tests. Its verdicts are
  the table below.

Not read by that review: the diffs of `test_non_finish_discrimination.py`,
`test_run_config.py`, `test_build_server_protocol.py`, `test_build_server_client.py` and
`test_cmd_resolve.py` (test names only), the `extension-api` and persona documents, most of
the `test_build_execute.py` rewrite beyond the new tree-kill and signal-forwarding classes,
and `manage-tasks/SKILL.md` in full. No test was run here; the merge-group run is the
evidence that the suite passes. The plan's own archived artifacts were not read.

## Deliverable Fidelity vs Spec

Deliverables are named by their source tag in the spec.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| PLAN-LB-12 D1 — a timed-out daemon job stops its whole process tree | shipped-as-specified | `_marshalld_supervisor.run_job` starts the job in its own session; `_stop_job_tree` sends SIGTERM to the group, waits up to 10 s for the group to empty, then SIGKILL. The test uses a grandchild that ignores SIGTERM and asserts it is gone and the status is `timeout` |
| PLAN-LB-12 D2 — the direct (non-daemon) build path does the same | shipped, with one accepted deviation and two small defects | `_build_execute._run_bounded` replaces both `subprocess.run` calls: own process group, group kill, SIGTERM/SIGINT/SIGHUP forwarded. Deviation: a SIGKILL sent to the wrapper's process group now leaves the build running, where before the build shared the group; a test pins this as an operator-accepted case, against the verify-first clause that forbade leaving more processes than before. Defects: see Follow-Ups |
| PLAN-LB-12 D3 — the pytest temp-root pruning never removes a live session's directory | shipped-as-specified | `build.py` `_session_owner_is_alive` and `_prune_basetemp_roots` exclude directories with a live owner from both bounds and keep a directory on any doubt. The test uses four directories with exact survivor sets. The Windows path of the owner probe was not exercised (the landing message says so) |
| PLAN-LB-12 D4 — a timed-out build names the bound that was applied and where it came from | shipped-as-specified | `run_config.timeout_resolve`, `marshalld._resolve_job_timeout`, the terminal payload and `_build_format.EXTRA_FIELDS` carry the three fields; assertions are exact. The daemon-to-supervisor-to-client chain is covered by separate unit tests, not by one end-to-end run |
| PLAN-LB-12 D5 — a gate build is attributed to its plan | partly shipped | The resolver now inserts `--plan-id` after `run` (`_cmd_client_handlers._attribute_build_executable`), and tests assert the submitted plan id. The document sweep covers `phase-6-finalize/**` and three named files, not every skill document the verify-first clause asked for. The change-ledger half is open: see Follow-Ups |
| PLAN-LB-01 D1 — several narrower green builds are credited together | shipped, with a minor deviation | `_freshness_crosscheck.row_contribution`, `union_contributors` and `_joint_contributors` implement the rule. The spec says the record names every contributing row; the code names the first adequate row per analysis, and the test expects two rows where the spec's done-condition lists three |
| PLAN-LB-01 D2 — a refusal names the analyses still missing | shipped-as-specified | `missing_analyses` sits beside `row_scopes`; the reason stays `build_scope_narrow`. Tests assert the lists exactly |
| PLAN-LB-01 D3 — the gate documents state the rule in one place | shipped; not read in full | `pre-push-quality-gate.md` and `push.md` point at `manage-tasks/SKILL.md`; `push.md` adds a `rows={N}` term |
| PLAN-LB-01 D4 — controls that must still refuse | shipped-as-specified, at unit level | `test_pre_commit_verify_freshness_union_controls.py` covers the five cases with exact reasons. Each stubs the required-coverage derivation, the ledger path and the SHA, so the real derivation is not exercised |

The freshness rule the gate now applies: one attributable green row at the current SHA that
covers the change alone is cited alone. Otherwise every required analysis needs at least
one attributable row that performs it at an adequate scope — whole-tree, or, for a change
that is not whole-tree, a scope that contains all of the change's modules. Scope is never
pooled across rows: several bundle-scoped verifies do not add up to a whole-tree or
multi-module change. The spec left that out on purpose.

Realized surface against the declared one: 25 of the 27 declared files were touched. The two
untouched are `execute-task/scripts/inject_project_dir.py` (the remedy not chosen) and
`test_pre_commit_verify_freshness.py`. 31 of the 56 changed files were not declared: four
scripts (`build_server.py`, `architecture.py`, `_ledger_core.py` — a comment only —
`_build_parse.py`), thirteen documents (among them `phase-5-execute/SKILL.md`,
`plan-marshall/workflow/execution.md`, `canonical_verify.md`, `build-server-client/SKILL.md`
and `execute-task/SKILL.md`) and fourteen test modules.

## Metrics and Anomalies

- Tokens: 13,122,777. Finalize alone recorded 7,235,372, 58 percent of the plan.
- Duration: 50,411 seconds wall time (about 14 hours; it ran overnight).
- 23 tasks, 7 of them fix tasks; 3 of those came from test failures that surfaced only at
  batch test runs, because the module-wide test command was too long for a leaf.
- The pre-submission self-review ran five rounds and returned 32 findings, all fixed, with
  no clean round. It was closed by operator decision (`acceptance=operator_override`) and
  was not re-run on the two later review-fix commits. It ran the review from before #1726.
- Both head-dependent project steps fired eight times with identical verdicts.
- `scope_creep_check` failed on all six calls.
- 30 of 34 dispatch-boundary rows carry no step id; the change ledger held no build row for
  the plan against 148 logged build calls.
- `archive-plan` is listed `pending` because the message was written before the archive
  move. `cleanup_owed=false`.

## Routing and Merge Behavior

- Review: CodeRabbit raised 11 comments over three rounds, 7 actionable, 6 fixed. One
  (944da6) was declined as a false positive but recorded `taken_into_account`.
- CI/merge: merged through the merge queue; the merge-group run concluded `success`.
- Collisions with plans in flight: PLAN-LB-24 and PLAN-LB-29 declare none of the 56 files
  as far as the earlier cross-check measured (PLAN-LB-23 was disjoint from both). The
  undeclared documents were not in that measurement.
- Consequence for staged plans: the commit changed files PLAN-LB-26 cites by line —
  `execution.md`, `phase-5-execute/SKILL.md`, `manage-tasks/SKILL.md`, `canonical_verify.md`,
  `build-server-client/SKILL.md` and `_build_execute_factory.py` — and `_build_shared.py`,
  which PLAN-LB-28 touches conditionally. PLAN-LB-26's bounded-wait deliverable
  (PLAN-LB-05 D4) describes `_route_to_daemon` as it was before this commit.
- After the move back, the main checkout's executor was unusable until regenerated (see the
  epic's Open Defects).

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-23 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-23 --field pr --value 1729`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-23 --field landing --value landings/PLAN-LB-23.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-23 --field plan_marshall_plan_id --value lb-23-verify-builds`
- [x] epic.md narrative reconciled against the queue rows (queue annotations)
- [x] Open Defects updated: the routed-build ledger entry; new entries for the direct
  build path's signal handling and for the main executor
- [x] Watches updated: self-review baseline, head-dependent steps (trigger met), rebases
- [x] resume anchor updated in `resume_anchor.md`
- [x] `queue-view.md` regenerated and committed with the row change

## Follow-Ups

- **The change-ledger half of PLAN-LB-12 D5 is open.** Builds now carry the plan id, so
  rows name the plan wherever they land. Where they land is unchanged: the ledger path is
  resolved from the working directory, each plan worktree has its own ledger file, and the
  freshness check takes the SHA from the plan's worktree but the ledger from its own working
  directory. The new routed-build test replaces the ledger path with a temp file, so it
  cannot see the split. Recorded as an Open Defect; not owned by a staged plan.
- **Three defects in the direct build path's signal handling**, all in `_build_execute.py`:
  `_signal_build_group` suppresses `ProcessLookupError` only, so a permission error from the
  group kill is reported as `error` and not as `timeout` (the supervisor twin handles it);
  the grace period waits on the group leader only, so the rest of the group gets SIGKILL
  without grace when the leader exits promptly; and the handlers are installed a few
  statements after the child starts, so a signal in that window kills the wrapper and
  orphans the build. Recorded as an Open Defect.
- The doc-contract sweep for the plan-id rule covers the finalize documents only.
- The union record names two contributing rows where the spec asked for all of them.
- PLAN-LB-26 and PLAN-LB-28 need their claims re-grounded against this commit before launch.
