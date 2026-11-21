envelope_version=1
sender_type=plan
sender_id=rb-lb-174-lb172-landing-defects
epic=live-blockers
kind=landing
created=2026-11-21T17:40:22Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-174-lb172-landing-defects
epic=live-blockers
pr=#2042
merge_state=merged
cleanup_owed=false
deliverables_total=6
deliverables_done=6
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2173
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=13
review_body_findings_handled=13
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (the guard log is `.plan/temp/guard.log`; no refusal was recorded for this run's sessions).

## Deliverables

Every Done-when below carries `order: test-first`: the test was written and run RED against the unfixed code before the fix, and the failing output identifier is a pytest node location from that run. No `mutation-after` is claimed.

**D1 — a post-run log fault stays a launch fault.** All four clauses met.
- `test_a_post_run_log_fault_keeps_its_class_reason_and_code[0]` / `[1]` — test-first, failing at `test_build_execute_routing.py:564` (`assert 0 == 1`); commit `dced868f1`.
- `test_a_subdir_constant_whose_first_part_is_not_dot_plan_still_creates_its_directory` — test-first, failing at `test_daemon_job_log_in_tree.py:332` (`assert 'failure' == 'success'`); commit `dced868f1`.
- the pre-spawn control holds; the existing build-server suites hold (72 + 11 + 50 passed).

**D2 — the carried-forward read binds through its status.** All clauses met.
- gate and facts refusals — test-first (`test_runbook_lane_sonar.py:823`, `test_runbook_lane_sonar_landing.py:337`); `test_a_carried_forward_read_never_answers_confirmed` — test-first (`test_read_open_issues.py:610`); the fallback sentence — test-first (`test_runbook_lane_sonar.py:842`); the conflicting-spelling refusal — test-first (`test_runbook_lane_sonar_landing.py:352`). Commit `685254722`; the analysis-revision pin followed in `e4da64b89`.

**D3 — a fence-only section counts, and the cap precedes the allocation.** All clauses met.
- `test_a_section_whose_only_content_is_a_fence_reads_a_finding_or_stops[summary-fence-only, summary-fence-inside-wrapper]` — test-first (`test_runbook_lane_review_gate.py:2866`); `test_the_body_cap_is_checked_before_any_row_beyond_it_is_built` — test-first (`:1147`, `1200 rows were built`); the parser suite holds (192). Commit `7283e593f`.

**D4 — a symlinked workflow is named, not skipped.** All clauses met.
- `test_a_symlinked_workflow_beside_a_regular_one_stops_the_read` — test-first (`test_runbook_lane_sonar.py:977`); the three text pins — test-first (`test_runbook_lane.py:1911`, `:1920`, `:1928`); the footprint suite holds. Commit `2ce108ce7`. The in-checkout branch gained its own test later (`test_a_readable_in_checkout_symlink_carrying_the_opt_in_stops_the_read`, red against the pre-D4 function, `f3934d264`).

**D5 — the manifest and `manage-config` refuse what they cannot read.** All clauses met.
- `test_a_malformed_commit_and_push_applies_the_floor` — test-first (`test_reconcile_backfill.py:141`); `test_a_malformed_callers_file_answers_the_documented_reason` — test-first (`test_orchestrator_scope.py:887`); the duplicated comment removed; reconcile (82 after the extra test), manifest (278) and orchestrator (1374) suites hold. Commit `75e7ff71c`. The malformed `plan`/`phase-5-execute` shapes followed (`8710751c0`, `f3934d264`).

**D6 — one owner for the re-read rule, and tests that can fail.** All clauses met.
- `test_no_document_states_a_second_answer_for_the_unexplained_difference` — test-first (`test_analyze_false_claim_contract.py:325`); the swallow-all control and the shell-out fixture — test-first (`:430`, `:457`, with the helper temporarily reverted to its swallowing shape); the parity guard — test-first (`test_apply_changes_command_parity.py:690`). The shared-slot clause was a READ: the rule is in `tools-integration-ci/SKILL.md:222-241`, so the hypothesis was refuted and no document changed. Commit `8d8f68559`.

Gate: `module-tests` green at `dc2ae54d2`, `75e7ff71c`, `f3934d264`, `8710751c0`, `d643753d5`, `fa8d39153`; `verify` green at `8d8f68559`, `d643753d5`, `49a90de15`, `0bd8a08af` and `fa8d39153`; CI `verify / verify` green on every head it ran.

## Personas and skills

- Production code (D1–D6 and every review fix): `persona-implementer`.
- Self-review rounds 1–3 and every PR-comment triage: `persona-code-reviewer`.
- Domain skills per deliverable were loaded as standards: D1 `ref-code-quality`, `python-core`, `pytest-testing`, `manage-build-server`; D2 `ref-code-quality`, `python-core`, `pytest-testing`, `runbook-lane`, `workflow-integration-sonar`; D3 `ref-code-quality`, `python-core`, `pytest-testing`, `runbook-lane`; D4 the same four; D5 `ref-code-quality`, `python-core`, `pytest-testing`, `manage-execution-manifest`, `manage-config`; D6 `ref-code-quality`, `ref-documentation`, `python-core`, `pytest-testing`, `plan-orchestrator`. No skill was dropped and no surface-drift skill was needed.

## Hypotheses

- The build-failure path renders a post-run `log_file_failed` as `build_failed` — CONFIRMED at `_build_shared.py:791` (leg gated on `exit_code == -1`), then by the red run.
- `_mask_fenced_code` blanks a fenced block, so a fence-only section reads empty — CONFIRMED at `runbook_lane.py:3088`/`:3771`, then by the red run.
- `sonar.py:1296` reports `confirmed` for a carried-forward read — CONFIRMED at `sonar.py:1296`, then by the red run.
- The CI does not follow a symlinked workflow — NOT TESTABLE here: `.github/workflows/python-verify.yml` is a regular file that opts in and delegates to a reusable workflow this checkout does not hold; no symlinked workflow exists. The lane's rule does not depend on the CI's own handling, because discovery never reads a link.
- `tools-integration-ci/SKILL.md` does not carry the shared-slot rule — REFUTED: the rule is there at `:222-241` (`--slot` under the `NO_PLAN` sentinel, `shared_body_slot_refused`).
- `decision-rules.md` makes a non-bool `commit_and_push` the documented default — REFUTED: the default is for an ABSENT key only (`:194`), so the code was wrong and the floor applies.

## Findings

- Self-review round 1: four majors (facts guard missing the retired spelling; malformed parent blocks still defaulting; the daemon subdir guarantee unpinned; the in-checkout symlink branches unexercised) and eight texts — all fixed in `f3934d264`.
- Self-review round 2: three residual nits — closed in `8710751c0` and `d643753d5`.
- Self-review round 3: three vocabulary passages — closed in `d643753d5`; nothing open.
- PR review (CodeRabbit, head `d643753d5`): 4 inline threads + 1 outside-diff + 4 nitpicks. Threads all fixed in `49a90de15` and resolved after a reply naming the commit; the outside-diff wrapper-gap check strengthened in `49a90de15`; nitpick `nitpick-1`/`nitpick-2` fixed in `49a90de15`; `nitpick-3` declined with a reason (the fixture cannot discriminate — the wrapper stops on its own content in every shape built); `nitpick-4` declined with a reason (deriving the benign set from the same rule files is tautological).
- PR review (CodeRabbit, head `0bd8a08af`): 4 more actionable comments (the `set` field, the normalization/stop pair, `extra-buildable` per job) — all fixed in `fa8d39153`, threads replied and resolved.
- Sourcery (optional) refused on its own quota twice and never reviewed; recorded, not gating.
- Final gate read: 0 unresolved threads, 13 body findings, 13 handled.

## Reviewers

- `coderabbit` (required, quota-limited, `review_complete_after_handling`): reviewed `d643753d5` with a marker-bearing summary whose `coveredCommitId` is that head, then reviewed `0bd8a08af` and `fa8d39153` automatically. Every finding handled; every thread resolved after a reply. No re-trigger was needed after `fa8d39153` (the flag plus the qualifying review).
- `sourcery` (optional): triggered twice, refused on its own review budget both times; its check later reported SUCCESS/SKIPPED without a review body. Not gating.

## Operator questions

None asked. No rule had to bend and no blocker arose; the only decision points were review dispositions, and each declined item carries its stated reason above and in the progress file.

## Rule check

- `executor-skew`: `not_applicable` (source checkout; executor `0.1.2173` maps this checkout's scripts).
- spec read: `spec_source=ledger_worktree`, no `spec_differ`.
- Guard: `present`. No guard refusal was recorded for this run's sessions, and the guard-log check counts only what it recorded; the run's own actions were re-checked against section 1 by hand.
- Shell/file-rule breaches: none issued by the run — every file read and search used the file tools, every script call went through `python3 .plan/execute-script.py …`, every build through the resolved `build` map, every CI action through `ci`. One accidental edit-in-flight occurred twice (the worktree was edited while a `module-tests` run was executing); both runs are recorded as invalidated and their heads re-run, which is a process error, not a rule breach.
- Restarts: none. Sub-agents: three self-review rounds, all completed; no killed sub-agent, no re-dispatch.
- The PR body names every out-of-surface change (`uv.lock`, `workflow-integration-sonar/SKILL.md`, `test_orchestrator_scope.py`, `test_sonar_analysis_revision.py`, `phase-4-plan/SKILL.md`) with its reason.

## Build server

- Setup preflight: `ready`.
- Every build ran `daemon_longpoll`; `in_process_fallback: 0`; no build fell back and none needed a launch-fault retry. No job was `killed`.
- The build-server preflight was re-answered per build by the routing client; no `--execution-mode` flag was ever passed.
- Runtime stamp: no `runtime_stamp_reason`.

## Residue

- `uv.lock` was regenerated and committed because `main`'s dependency bumps had left it stale; named in the PR body.
- `/apply-changes` is owed on this repository after a bundle change, as this plan edits bundle sources.
- The two declined review nits (`nitpick-3`, `nitpick-4`) are recorded with their reasons in the progress file and on the PR; neither is a defect.
- The `confirmed_read_without_count` / `confirmed_zero_with_open_keys` / `confirmed_read_without_rules` reason identifiers keep the word "confirmed" while also applying to a `carried_forward` read; the lane text now says they name a measured read. Renaming them was judged a contract change beyond this plan.
