envelope_version=1
sender_type=plan
sender_id=rb-lb-101-review-policy-barrier
epic=live-blockers
kind=landing
created=2026-10-30T05:34:29Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-101-review-policy-barrier
epic=live-blockers
pr=#1890
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2025
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

## Deliverables

**D1 — an unreadable roster is an error, never an empty roster. MET**, order `mutation-after`.
- Evidence: `test/plan-marshall/automatic-review/test_roster_read_failclosed.py` — `TestTheReadDistinguishesUnreadableFromEmpty::test_an_unreadable_read_is_an_error_carrying_no_bot_list`, `test_a_readable_empty_roster_is_a_success_with_empty_lists`, `test_the_two_records_are_distinguishable_on_the_read_flag`, `test_a_list_shaped_roster_override_is_read`, `test_a_roster_that_cannot_be_parsed_is_unreadable`, `TestTheCommandLineFailsClosed::test_the_command_returns_non_zero_on_an_unreadable_roster`, `test_a_non_zero_exit_is_an_error_even_when_its_stdout_parses`, `test_a_zero_exit_with_a_parseable_payload_is_read`, plus the doc-contract tests.
- Failing run: `189f6e571` with `read_roster` mutated so an unreadable read returned `status: success` / `roster_read: true` / empty lists — `test_an_unreadable_read_is_an_error_carrying_no_bot_list` failed `assert 'success' == 'error'`, and two siblings failed with it. Restored; working tree clean at the mutation boundary.
- Consumers: `automatic-review/SKILL.md` (FIND, participation guard, trigger B) and the pre-merge barrier both read through the verb and stop on `roster_unreadable`; `pre_merge_gate._read_roster` shares the same contract and sets `require_zero_exit` on its own seam. Commit `189f6e571`.

**D2 — a stale required bot is triggered before the barrier asks. MET**, order `mutation-after`.
- Evidence: `test/plan-marshall/automatic-review/test_review_policy_defaults.py` — `TestTheBarrierSpendsTheLoopBeforeItAsks::test_a_stale_required_bot_is_triggered_before_the_question`, `test_the_question_carries_whether_a_trigger_was_attempted`, `test_the_trigger_scope_names_only_the_stale_member`, `test_the_pre_ask_refresh_runs_on_the_ask_path_only`, `test_the_trigger_state_is_initialised_before_either_blocked_path`.
- Failing run: `0c947b27` with the step-1 heading renamed and the `**Stale re-review**: {trigger_state}` prompt line removed — three tests failed (`ValueError: substring not found` ×2, `assert '{trigger_state}' in prompt`). Restored. Commit `189f6e571`, clarified in `0c947b27`/`f8fc2fa47`.

**D3 — no shipped document and no generated option moves a required bot to `optional_bots`. MET**, order `mutation-after`.
- Evidence: `test/plan-marshall/automatic-review/test_required_bot_demotion_contract.py` — the real-corpus sweep and `test_a_planted_offer_is_reported`, `test_a_prohibition_is_not_an_offer`, `test_a_prohibition_later_in_the_same_sentence_does_not_launder_the_offer`, `test_an_already_optional_bot_is_not_a_demotion`, `test_the_roster_token_form_is_seen`, `test_an_offer_that_names_only_a_reviewer_is_seen`, `test_the_disable_this_reviewer_label_is_seen`, `test_a_semicolon_ends_the_negation_clause`, `test_a_short_form_destination_is_caught`, `test_a_table_row_is_read_as_its_own_claim`.
- Failing run: `189f6e571` with the old "accept the decline (move it to `optional`, …)" sentence reinstated in `branch-cleanup.md` — the corpus sweep reported it. Restored. The scanner was then hardened twice (clause-local negation, wrapped-line join, `required_bots` and reviewer-only phrasings, the withdrawn "disable this reviewer" label, semicolon clause boundary) after its own findings.
- The four cited sites now name a recorded merge authorization; `plan-marshall/workflow/execution.md` and the structural option set were corrected in the same sweep.

**D4 — a quota refusal on a required bot is waited out by default. MET**, order `mutation-after`.
- Evidence: `test_review_policy_defaults.py` — `test_the_window_default_is_the_policys_own_window` (90 min → 5400 s in the knob and in `merge_lock`), `test_the_attempt_cap_is_the_policys_own_count` (10), `test_the_gate_defaults_to_true`, `test_the_documented_off_switch_survives`, `test_an_optional_bot_refusal_never_arms_a_wait`, `TestCloseAndReopenIsBoundToNoReviewOnRecord` (4 cases), `test_an_awaitable_refusal_is_waited_out_before_the_question`, `test_the_quota_wait_honours_the_documented_off_switch`; `test_config_defaults.py` (true/5400); `test_merge_lock_rate_window*.py` (10/5400).
- Failing run: `189f6e571` with `review_rate_window_await` flipped back to `false` — `test_the_gate_defaults_to_true` failed `assert 'false' == 'true'`. Restored. Commit `189f6e571`, extended in `15403f69`/`4174b575`/`d6049de10`.

**Per-head test runs** (targeted, scoped while iterating): `189f6e571` (roster, demotion, policy), `58962a866` (demotion), `413df9ca5` (roster, policy, demotion, pre_merge, rate_window, structural_refusal, attempt_held), `0c947b27` (policy + full suite), `15403f69` (branch_cleanup, demotion, policy), `4174b575` (pre_merge, policy), `d6049de10` (pre_merge, quality-gate), `f07d14e3` (quality-gate). Full `module-tests` ran at `189f6e571^` (27467 passed; 6 old-default failures, all updated) and at `0c947b27` (32551 passed, 11 skipped, 2 host-load timeouts — see Residue). CI's own `verify` job is green on every final head, including `f07d14e3`.

## Personas and skills

- production code (`review_completeness.py`, `pre_merge_gate.py`, `github_re_review.py`, `merge_lock.py`): `persona-implementer`
- unit/module tests: `persona-module-tester`
- documentation (`SKILL.md`, `branch-cleanup.md`, standards, `doc/user/*.adoc`): `persona-documenter`
- every self-review round and every PR-comment triage: `persona-code-reviewer`
- The spec declares no `Skills:`/`Persona:` lines: **skills: none named** for every deliverable. No skill was added for surface drift; the extra files are documentation ripple from D3's own requirement, recorded below.

## Hypotheses

- **HYPOTHESIS: the policy numbers (90 minutes, up to ten) differ from the knob defaults (3600 s, cap 6) — CONFIRMED.** `automatic-review/standards/coderabbit.md` § "Operator review policy" states 90 minutes / ten windows; `merge_lock.py` shipped `_DEFAULT_RECOVERY_ATTEMPT_CAP = 6` and `_DEFAULT_WINDOW_SECONDS = 3600.0`. Both now follow the policy (10 / 5400), with the reason recorded at the definition site.
- **HYPOTHESIS: the barrier's option set is authored in prose at the `ask` sites rather than generated by a script — CONFIRMED.** `branch-cleanup.md` carries hand-written `AskUserQuestion` blocks; `pre_merge_gate.py` renders no options. D3 therefore needed the scanner only, no generator.
- (D2 verify-first) the first-pass stale trigger belongs in the barrier, not the leaf: the barrier is the site about to ask, and `automatic-review`'s trigger B already triggers a stale required bot on loop-back re-entry, so doing both would ask one bot twice for one head. Recorded in the prose and pinned by `test_the_pre_ask_refresh_runs_on_the_ask_path_only`.
- (D4 verify-first) the wait is held by the main context (`phase-6-finalize` item 7a) and the merge mutex is released across it: confirmed, and the barrier states the release plus "no merge lock is held across the wait".

## Findings

- **Self-review round 1** (20 findings: 1 blocker, 7 major, 9 minor/nit) — all fixed in `413df9ca5`/`0c947b27`; the blocker was a surviving demotion offer in `plan-marshall/workflow/execution.md` that the scanner could not see.
- **Self-review round 2** (N1-N6) — all fixed: the cap narration named an option the escalation does not offer; the barrier's knob read named a source that does not carry it; three prose guarantees were unpinned; one unused import; a missing `\b`; a relocated initialisation.
- **Self-review round 3** — every code/doc/test finding confirmed fixed. Only a record-level item stayed open: the staged spec's Expected Surface under-declares the touched files and calls `bot-participation-contract.md` out of scope although D3 required changing it. The operator chose "Continue, record the drift".
- **CodeRabbit (22 findings over 8 review rounds, all fixed or answered, every thread resolved):** Branch 3's missing producer read; Branch 4 step scoping; the structural-refusal demotion arm in the hook and five shipped docs; the scanner's blind spots (reviewer-only phrasing, `required_bots`, the "disable this reviewer" label, clause-local negation, wrapped lines); the barrier not re-reading after a stale re-review; the retain-vs-release claim after a refused re-review; post-vs-await failure; non-zero roster exits in both readers; the roster failure detail; the "opt-in" wording; the unreadable-window qualification.
- **CI:** one `test-compile` failure on `df35ac92` (`no-any-return` from an untyped `get_skill_dir`) — fixed, and the missing local gate recorded. One full-suite failure on `e08613c7` (`test_cmd_re_review_short_circuits_on_await_failure` pinned the old envelope) — retargeted.
- **Pre-existing assertions changed (none weakened):** `test_shipped_attempt_cap_default_is_six` → `…_matches_the_operator_policy` and `test_sixth_attempt_is_admitted…` → `test_the_tenth_attempt_is_admitted…` (6/5 → 10/9); `test_config_defaults.py` False/3600 → True/5400; `test_merge_lock_rate_window_budget.py` 3600 → 5400; the shared rate-window fixture's cap now derives from the module; `test_the_orchestrator_hook_offers_the_three_real_remedies` → `…_the_two_real_remedies` and `test_the_contract_forbids_an_await_on_the_member` now asserts the demotion arm is absent; `test_cmd_re_review_short_circuits_on_await_failure` now asserts the preserved post outcome; four test docstrings describing the old remedy set were reworded.

## Reviewers

| Reviewer | Required | History | Disposition |
|---|---|---|---|
| coderabbit | yes (`quota_limited`) | reviewed `0c947b27`, `bdb33ec54`, `f8fc2fa47`, `af05e7c80`, `7fc41f19`, `4174b575`, `ff6af6ac`; refused 16:29, 17:04, 20:02, 21:35, 23:57, 00:49 ("Review rate limited"; "Next included review available in 38 minutes" at the last one) | **Standing review authorization applied.** Qualifying review on `ff6af6ac` (`coveredCommitId: ff6af6ac…`, `kind=reviewed`); every finding from that review and every later one fixed or answered, every thread resolved; re-triggered once after the last push (`f07d14e3`) and the refusal recorded; every other gate green on `f07d14e3`. The reviewed head is one commit behind the merge head; that commit is the exact fix CodeRabbit requested (the four "opt-in" references), so the gap is the re-review itself, not an unexamined change. |
| sourcery | no | refused on size: "your pull request is larger than the review limit of 150,000 diff characters" | Optional bot; ordinary settle, no wait, no action. |

## Operator questions

1. Text: "Self-review reached its 3-round limit. Every code/doc/test finding from rounds 1-3 is fixed and verified green, except one record-level item the run cannot fix: the staged spec's 'Expected Surface' under-declares the files this plan had to touch … How should the run proceed?" — options: "Continue, record the drift (Recommended)" / "Stop before the PR" — **selected: "Continue, record the drift"**.

Free-text operator messages: none.

## Rule check

- `guard: present`. Two guard refusals are attributable to this run's session (`ses_e7873f394ffeL6aXYr4HIleVO4`): **R1** at 12:51:22 for a piped shell command (`grep … | head`) while reading a build log, and **R5** at 18:20:13 for `python3 .plan/execute-tool …` — a typo'd executor name. Both were corrected immediately; no workaround was attempted. Every other guard-log line belongs to another session.
- **Build routing:** the setup preflight answered `ready`, and the first routed `module-tests` failed with `build_failed` and an EMPTY nested log (`pwx module-tests`, exit -1 at 0s) — the daemon could not spawn the wrapper. Every later build ran `--execution-mode in_process` (mechanism `in_process_fallback`), a deliberate degradation recorded here rather than retried.
- **Full-suite module-tests:** the two runs at `0c947b27` failed only `test/test_harness_shape_guards.py::test_every_predicate_examines_a_non_empty_population` and `::test_no_predicate_reports_a_module_it_could_not_parse` — pytest-timeout (>300 s) inside the whole-tree AST scanners, in a module this plan does not touch, with the host load average at ~198. Every module this plan touches is green under targeted runs, and CI's `verify` job runs the same full suite green on each final head.
- **Spec read:** `spec_source=ledger_worktree`; no `spec_differ` marker. **executor-skew:** `not_applicable` (source checkout; the executor maps this checkout's own scripts).
- **Worktree executor:** refreshed after adding the `roster` verb (`executor_regenerated: true`); the new verb was then run through the worktree's executor.
- Every build went through the resolved build command, every script through the executor, every CI action through `ci`. One wrong-notation call (R5) is reported above.

## Build server

- Setup preflight: `ready` (`registered: true`, version 1).
- First routed build: failed (`build_failed`, empty nested log, `pwx` spawn), so every build afterwards ran `--execution-mode in_process` (`mechanism: in_process_fallback`).
- No `killed` job. `executor_in_worktree: present`.
- `runtime_stamp_reason`: none reported.

## Residue

1. **Spec surface drift (record-level).** The staged spec's Expected Surface omits `github_re_review.py`, `doc/user/configuration.adoc`, `doc/user/parallelism-and-locking.adoc`, `workflow-integration-github/SKILL.md`, `pr-review-operations.md`, `automated-review-lifecycle.md`, `cuioss-review-bot.md`, `manage-locks/SKILL.md`, `plan-marshall/workflow/execution.md` and the touched tests, and its "Adjacent to … does not change" line names `bot-participation-contract.md`, which D3 itself required changing. The run cannot edit `.plan/orchestrator/`; the orchestrator should correct the ledger.
2. **Standing-authorization gap.** CodeRabbit's qualifying review covers `ff6af6ac`; the merge head is `f07d14e3`, whose only delta is the four "opt-in" → knob-name edits CodeRabbit requested. Its re-trigger after that push was rate-limited and the refusal is recorded.
3. **Host-load timeouts.** The two whole-tree scanner tests above are unverified-green locally on this host under load; they pass in isolation and CI runs them green.
4. **Tracked file churn:** none — the worktree was removed with a clean status, the local branch pruned, and the main checkout fast-forwarded to the merge commit `993423ac5`.
