envelope_version=1
sender_type=plan
sender_id=rb-lb-172-consolidated-leftover-fixes
epic=live-blockers
kind=landing
created=2026-11-20T21:54:53Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-172-consolidated-leftover-fixes
epic=live-blockers
pr=#2036
merge_state=merged
cleanup_owed=false
deliverables_total=10
deliverables_done=5
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2173
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=48
review_body_findings_handled=48
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

# PLAN-LB-172 — merged as `78951e23c` (PR #2036)

guard: present on this harness; no refusal beyond the two recorded below.

## Deliverables (Done-when grading)

The run RESUMED an interrupted session: D1–D5 were already committed on the branch and are green on
the tree, but their red-run logs were not preserved, so under the Evidence rule their Done-whens are
`not evidenced` by THIS session. D6–D10 were implemented here, each with a red run on the detached
base tree at `c22d103fb` and a green run after. `deliverables_done=5` therefore counts the five
fully evidenced deliverables; D1–D5 are shipped and tested but their `test-first` artifacts belong
to the interrupted session's record (the PR body it wrote).

| # | Verdict | Order | Test(s) | Failing run | Green at |
|---|---------|-------|---------|-------------|----------|
| D1 | met on the tree; **not evidenced** (carried) | test-first (carried) | 12 parser tests in `test_runbook_lane_review_gate.py` + the property test | recorded by the interrupted session | `a39aa80d6` |
| D2 | met on the tree; **not evidenced** (carried) | test-first (carried) | `test_runbook_lane_sonar.py`, `test_read_open_issues.py`, `test_runbook_lane_sonar_landing.py` | recorded by the interrupted session | `54fe92366` |
| D3 | met on the tree; **not evidenced** (carried) | test-first (carried) | retry-class table pin, classifier tests, document pins | recorded by the interrupted session | `93d55c4b3` |
| D4 | met (end-to-end after `043762307`) | test-first (carried) | `test_ci_base_cli.py`, derived-slot test, §6 slot pin | recorded by the interrupted session | `28e051041`, `043762307` |
| D5 | met on the tree; **not evidenced** (carried) | test-first (carried) | both contract tests, worked example | recorded by the interrupted session | `6ebc69cf4` |
| D6 | met | test-first | `test_a_withholding_field_in_either_gap_config_is_detected`, `test_no_entry_point_states_the_absence_of_a_key_as_a_fact_about_the_harness` | `c22d103fb`, log `62d28ec59ac94978837a0370a5ad4bfe.log` | `321aac6c3` |
| D7 | met | test-first | `test_an_unreadable_main_file_is_refused_naming_it`, `test_a_non_object_main_file_is_refused_naming_it`, `test_an_invalid_json_main_file_is_refused_naming_it`, `test_an_invalid_json_callers_file_refuses_instead_of_crashing` | `c22d103fb`, log `e3801e302c2646ed82d672e7e7e11740.log` | `29d0254c7` |
| D8 | met | test-first | `test_an_absent_verdict_closes_nothing_on_a_rewrite_authorization`, `test_a_rewrite_never_downgrades_a_retirement_decision`, `test_a_non_list_criteria_on_a_refused_retired_row_keeps_its_shape_error`, `test_a_refused_retirement_publishes_the_rows_grading_findings`, `test_the_unrecordable_retirement_states_carry_their_own_code`, `test_a_retired_deliverables_criteria_no_longer_cover_a_spec_clause`, `test_a_snapshot_with_no_recorded_freeze_is_present_not_frozen`, `test_the_decision_type_flag_reaches_the_commit_through_the_parser` | `c22d103fb`, log `4dabe18d90474641af2f447f19d1d2d1.log` | `0e6e52bdc` |
| D9 | met | test-first | `test_push_only_candidates_are_refused_on_a_local_only_plan`, `test_the_same_candidates_are_backfilled_when_pushing`, `test_a_refused_always_is_logged_and_reports_the_applied_gate`, `test_the_same_gate_is_applied_when_pushing` | `c22d103fb`, logs `b9ae7831825840fdaf077c71de372a1d.log`, `57a44fbcf2e4499c82c09b6b4875540e.log` | `976e24c2d` |
| D10 | met | test-first | `test_a_symlinked_parent_directory_is_refused`, `test_a_spawn_failure_releases_the_sink_and_removes_the_log`, `test_a_log_that_vanishes_under_the_job_is_reported_as_a_logging_failure`, `test_the_log_directory_follows_the_subdir_constant`, `test_every_created_directory_component_is_private`, `test_wait_log_file_fault_preserves_its_class_and_reason`, `test_daemon_log_file_fault_reaches_the_caller_with_its_reason` | `c22d103fb`, logs `9e750bb3dffa47ab962f7335f96c6b3f.log`, `8681eedc50324dc6bc75bd6f320b7488.log`, `e2e5f03e2545445fb66942eb34b7f60d.log`, `c7af23c6bd9345fba7a75ee5ca828f42.log` | `1acfd12f9` |

Per-head test runs after each pushed head: `test_runbook_lane` (516/517), `test_orchestrator_use_worktree`
(26), `test_reconcile*` (81), `test_ceremony_finalize_selection*` (75), `test_daemon_job_log_in_tree`
(10), `test_build_execute_routing` (70), `test_build_server_client` (41), `apply-changes` (24),
`test_retirement_decision_d4` (24), `test_read_open_issues` (27). `verify` green at `36148a439`
(local) and CI `verify` green at `36148a439`.

## Personas and skills

- `persona-implementer` for all ten deliverables; `persona-code-reviewer` for the self-review round and
  every PR finding; `persona-module-tester` for the tests.
- Domain skills loaded per deliverable: `plan-marshall:ref-code-quality`, `pm-dev-python:python-core`,
  `pm-dev-python:pytest-testing` (all), plus `plan-marshall:runbook-lane` (D1–D4),
  `plan-marshall:workflow-integration-sonar` (D2), `pm-documents:ref-documentation` (D3, D5, D6),
  `plan-marshall:plan-orchestrator` (D5), `plan-marshall:manage-config` (D7),
  `plan-marshall:manage-solution-outline` + `plan-marshall:phase-6-finalize` (D8),
  `plan-marshall:manage-execution-manifest` (D9), `plan-marshall:manage-build-server` (D10).
  No skill was added for surface drift beyond the two files named as outside the surface
  (`build-server-client/build_server.py`, `script-shared/build/_build_execute_factory.py`).

## Hypotheses

Not re-read by this session; the spec's HYPOTHESIS lines were answered by the interrupted session
(D1 parser paths confirmed by constructed inputs; D3(a) code-not-text; D2(e) no code change;
D5(b) triage.md confirmed). The ones this session acted on:
- "the plan-id fold is a valid body slot" — REFUTED as an identity claim: the fold is lossy, so the
  plan id and the slot are now separate values (`043762307`).
- "a wrapper's content check masks the group" — CONFIRMED as an under-count; the mask is now the
  group's own summary plus the child block (`47ef56202`, `36148a439`).
- "`read_json(..., default={})` reports a corrupt file" — REFUTED; it reads as an absent key, now a
  sentinel (`dccf0e557`).

## Findings

Five CodeRabbit reviews (13:48, 15:34, 16:41, 17:54, 19:54) produced 21 inline threads and 48
review-body findings. Every thread was answered and resolved; all 48 body findings carry a disposition:
45 name the commit that closed them (`47ef56202`, `cb9674739`, `b5fc1c0c0`, `a611312f7`,
`dccf0e557`, `36148a439`), and 3 are declined with a stated reason — the pre-allocation cap check, the
caller-asserted `count-status-reason` provenance, and the full ancestor descriptor-chain walk (each
answered on its thread with the reasoning). The self-review round raised three real defects and all
were fixed before the merge: the body slot was never passed end-to-end, the reconcile config read was
fail-open on a corrupt file, and the mention index mixed masked/raw occurrences.

## Reviewers

- coderabbit (required): reviewed heads `a8bd2ffac`, `321aac6c3`, `976e24c2d`, `b5fc1c0c0`,
  `043762307` (quota-limited; `review_complete_after_handling` applied once a qualifying review was on
  record — its summary carries the `final_review_risk_coverage` marker naming the covered commit).
- sourcery (optional): refused by the provider (diff over 150,000 characters); never gating.

## Operator questions

None asked in this session; none asked by the interrupted session that survived in its record. No
free-text operator messages were used as authority.

## Rule check

- `executor-skew`: `not_applicable` — the lane text lives in this source checkout, so the executor maps
  the checkout's own scripts.
- Spec read: `spec_source: ledger_worktree`; `spec_differ` not reported.
- Deviations, self-reported: one shell redirect of `ci pr comments` output to `.plan/temp/` (a
  diagnostic read of a large TOON body); one guard-refused `python3 -m json.tool` attempt and one
  guard-refused shell-chained command (neither retried around the guard); one guard-refused `cp`
  attempt, replaced by file-tool edits on the base tree; two builds submitted concurrently once (the
  per-directory lock serialised them, the second reporting `queued_seconds: 41`).
- Guard: `guard: present` on this harness; the log carries the two refusals above and no others for
  this session tree.

## Build server

Setup preflight `ready`. Every build was `daemon_longpoll`; no `in_process_fallback` and no
`launch-fault-retry`. Two `verify` runs exceeded the 300 s long-poll and were RE-ATTACHED with
`build_server wait --job-id … --bound 1302` in the same call (both finished green). No `killed` job.

## Residue

- `/apply-changes` is OWED: this plan edits bundle sources, so the targets, harness installs, executor
  and registry pin must be carried before a session sees the new skill text.
- **PLAN-LB-173 is staged and now redundant.** The orchestrator staged it to carry PR #2036 to merge and
  to deliver D6–D10; this run did both. Its plan file and queue row should be retired or re-scoped.
- `landings/PLAN-LB-172.md` in the ledger records the earlier PARTIAL run (`merge_state: open`); the
  row is still `running` and needs reconciling to `shipped` with this merge commit.
- Three review findings are declined, not deferred: the pre-allocation cap refinement, the
  caller-asserted reason provenance, and the ancestor descriptor-chain walk. Each is recorded on its
  thread with the reason it is accepted.
- The interrupted session's `test-first` artifacts for D1–D5 were not preserved; the tests are green
  and the red-run claims live only in the PR body it wrote.
