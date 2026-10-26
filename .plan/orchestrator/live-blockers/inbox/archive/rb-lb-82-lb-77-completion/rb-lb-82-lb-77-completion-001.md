envelope_version=1
sender_type=plan
sender_id=rb-lb-82-lb-77-completion
epic=live-blockers
kind=landing
created=2026-10-26T10:59:39Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-82-lb-77-completion
epic=live-blockers
pr=#1864
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2010
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=0
step.sonar-roundtrip.open_issue_rules=none
```

guard: present

# Landing report — PLAN-LB-82 (lb-82-lb-77-completion)

Merged as `931d5847b9`

## 1. Deliverables

All four deliverables are fully met; every Done-when is met as written.

| DW | Verdict | Test | order | Failing run | Commit |
|---|---|---|---|---|---|
| D1: a `write_status` whose in-guard read fails keeps `criteria_integrity` + `functional_review_override_heads` and reports it | met | `test_a_failed_in_guard_read_refuses_the_write_and_keeps_the_keys` (4 reasons: missing / unreadable / corrupt / not_object), `test_a_corrupt_document_is_reported_and_left_alone`, `test_a_write_for_a_plan_with_no_status_document_commits_nothing` | mutation-after | `782d32e3f` + reverted fix — 9/16 failed (`DID NOT RAISE StateReadFailed`, bytes changed) | `782d32e3f` |
| D1: `create --force` over a plan carrying both keys yields a status without them | met | `test_create_force_yields_a_status_without_the_protected_keys` | mutation-after | same run (`criteria_integrity` survived) | `782d32e3f` |
| D1: finalize-steps `set-lane` keeps a block committed inside the window | met | `test_a_block_committed_while_the_lane_write_enters_the_guard_survives`, `test_the_lane_write_commits_through_the_guarded_read_modify_write`, `test_a_malformed_override_map_is_refused_without_touching_the_document` | mutation-after | same run (`KeyError: criteria_integrity`) | `782d32e3f` |
| D2: a `write_snapshot` in the record-then-log window waits or is `snapshot_busy` and consumes nothing | met | `test_a_write_snapshot_started_inside_the_log_window_consumes_nothing` | mutation-after | `f45c33f9e` + guard/token/kept reverted — 4/11 failed | `f45c33f9e` |
| D2: an older failing log withdraws only its own authorization | met | `test_a_newer_authorization_survives_an_older_failed_log` | mutation-after | same run (`withdrawn`, newer deleted) | `f45c33f9e` |
| D2: a double fault leaves no standing authorization without a log line | met | `test_a_failed_digest_withdrawal_fails_closed_as_tampered`, plus later `test_a_prior_unlogged_authorization_is_not_restored`, `test_a_pending_authorization_does_not_permit_a_refreeze` | mutation-after | same run (`kept: the snapshot still holds it`); both later tests failed under their own mutations (`ea6f4de82`, `3832de127`) | `f45c33f9e` |
| D2: docstring + `review-rubric.md` L42 contradict nothing (doc-contract on the vocabulary) | met | `test_the_authorization_outcome_vocabulary_matches_its_documents` | mutation-after | same run (undocumented: rolled_back, tamper_flagged, inconsistent) | `f45c33f9e` |
| D3: a `C9` row whose text equals criterion 1's frozen text yields `unmatched_criterion` | met, narrower than it reads | `test_an_id_bearing_row_whose_text_equals_another_frozen_criterion_is_reported` | mutation-after | `389d4e282` + predicate/rollback/withdrawal mutations — 8/36 failed | `389d4e282` |
| D3: the replaced rollback test fails on a raw `os.write` regression | met | `test_a_fault_at_the_atomic_replace_leaves_the_committed_bytes_and_says_so` | mutation-after | same run (`NOT fully rolled back` missing) | `389d4e282` |
| D3: each replaced or new test fails under a mutation of the code it names | met | `test_a_write_snapshot_whose_digest_cannot_be_recorded_restores_the_prior_bytes`, `test_the_write_snapshot_rollback_does_not_erase_a_newer_commit`, `test_a_failed_log_restores_a_prior_authorization`, `test_a_withdrawal_that_cannot_be_written_is_reported_as_not_withdrawn`, `test_a_consumed_authorization_reports_already_consumed`, `test_the_protected_set_is_exactly_the_keys_a_verb_writes_at_top_level`, `test_a_deliverable_qualified_id_answers_only_inside_its_deliverable`, `test_a_deliverable_qualified_id_leaves_the_other_position_open` | mutation-after | same run (8 failures, one per named mutation) | `389d4e282`, `9b654c515` |
| D4: a file replaced through `atomic_write_bytes` keeps its previous mode | met | `test_a_replaced_file_keeps_its_previous_mode` | test-first | `389d4e282` (file_ops unchanged since `4eb58fbc1`) — 3/5 failed (mode `0600`) | `3482f74a3` |
| D4: an `os.fdopen` failure leaves no open descriptor and no temp file | met | `test_an_fdopen_failure_leaves_no_open_descriptor_and_no_temp_file` | test-first | same run (`os.fstat` did not raise) | `3482f74a3` |
| D4: the temp file is fsynced before the replace (call order) | met | `test_the_temp_file_is_fsynced_before_the_replace` | test-first | same run (no fsync before the replace) | `3482f74a3` |

Per-head test runs: `lb77_` 39→43 (green at each of `bfa27b50e`, `ea6f4de82`, `3832de127`, `9751f3b66`, `a3b6144c8`, `414d900e1`); `atomic_write_bytes_durability` 5; `safe_main` 14; `locks` 653; `file_ops` 95; `predicate` 194 (both shape-guard flakes green in isolation); `lb74` 29; `criteria` 70. Full-suite runs: `6ee142063` 32246 passed; `414d900e1` 32254 passed; `66c883e51` timed out at the 2700 s bound with no result; the two `test_harness_shape_guards.py` pytest-timeout flakes were the only failures in every run that finished.

D3 caveat, recorded in the test: `run_author_verdict` refuses an out-of-range `criterion_id` at seal time, so a `C9` row cannot be author-sealed; the validator's contract is driven at `report_unmatched_rows` directly, with the gate predicate asserted alongside and a sealable `D1.C2` row covered end to end.

## 2. Personas and skills

Persona applied: `plan-marshall:persona-implementer` (every deliverable's declaration) for production code, `persona-code-reviewer` for every self-review round and every PR comment triage, `persona-module-tester` for the test work. Domain skills per deliverable, as declared: `pm-plugin-development:plugin-architecture`, `pm-plugin-development:plugin-script-architecture`, `pm-dev-python:python-core`, `plan-marshall:ref-code-quality`, `pm-dev-python:pytest-testing`, `plan-marshall:persona-module-tester`. No skill was added for surface drift.

## 3. Hypotheses

The spec carried one HYPOTHESIS (a transient in-guard read failure is reachable) and one on lock order; both were already corroborated in the Claim Labels and re-confirmed here: `_locks_core.py` L314-324 returned `{}` for OSError/JSONDecodeError/non-dict and `rmw_json` handed it to the mutator (confirmed, pre-fix), and `_crash` lock order is snapshot guard → status guard everywhere (`_snapshot_guard`, `write_snapshot`, `authorize_change`, `_merge_integrity`) with no reverse-order path (confirmed). The verify-first clause resolved as: **the create seed bypasses the carry** (`carry_protected_keys=False`) rather than clearing keys inside the guard, because the keys it must not inherit belong to the document it replaces; and **the `kept` double fault fails closed** (`tamper_flagged`) rather than logging out of band, because the edit is already gone and the record's digest binding then reads `tampered`, so the artifact is refused until repaired.

## 4. Findings

Self-review rounds: 5 rounds, all dispositions applied.
- Round 1: 1 blocking (the `write_snapshot`-site rollback test could not fail on a dropped `expected=`) + 10 advisory → fixed in `f8f5a79b1`; later the full suite caught that the same commit had bypassed the `record_integrity` seam, fixed in `9751f3b66`.
- Round 2: 7 advisories (dead `already_consumed` arm, overstated vocabulary-test summary, fsync causal claim, tamper repair route, unnamed guard timeout, CLI docstring gap, substring writer match) → `9b654c515`.
- Round 3: 3 cheap items (scoped "carried regardless", qualified-call scan, descriptor-identity order test) + 1 residual (two-call double fault) → `bfa27b50e`; the operator authorised a 4th round for the residual.
- Round 4: residual fixed (`ea6f4de82`) and the same fail-open's CONSUMPTION path found → `3832de127` (`_write_snapshot_locked` refuses a pending authorization) plus a test for the token-gated marker clear.
- Round 5: **no findings, open items none**.

CI findings: none on the final head. PR comments: CodeRabbit posted 4 findings — 2 adopted (`a3b6144c8`, `414d900e1`), 1 already addressed in `ea6f4de82`..`3832de127`, 1 reasoned dismissal (StrEnum refactor); all four threads resolved, and the bot itself marked two as addressed. Sourcery: quota-refused, no findings.

## 5. Reviewers

| Reviewer | Kind | Result | Head reviewed | History |
|---|---|---|---|---|
| coderabbit | required, `quota_limited` | **reviewed** | `a3b6144c8` (`final_review_risk_coverage` `sourceCommitId`/`coveredCommitId` = `a3b6144c8`, `kind=reviewed`, Merge Risk *Low*) | triggered at branch open, after `bfa27b50e`, after `ea6f4de82` (refused: "already reviewed the last commit"), after `a3b6144c8` (`@coderabbitai full review`, refused: rate limit, next included review +54 min), after `414d900e1` (silent) and after the base merge `66c883e51` (silent). |
| sourcery | optional, `quota_limited` | refused | n/a | trigger posted twice; the bot refused on its 7-day 250k-diff-character budget ("request another review in 1 day and 16 hours"). Optional, never gating. |

**Standing review authorization** (the required reviewer is `quota_limited`): a qualifying review exists on a3b6144c8; every finding from it is fixed or answered and every one of its threads is resolved; it was re-triggered after the last push and the silence is recorded; every other gate condition holds on the current head (CI green, Sonar 0, all comments handled). The operator also directed landing without a further CodeRabbit review, and selected "Merge now at this head, both gaps as stated" for the gaps below.

## 6. Operator questions

1. Message: "The step-0 executor skew check returned `could_not_check`, not `match` … How should I proceed?" — options: *Proceed using the surface check*, *Regenerate the executor first*, *Stop the run as blocked*. **Selected: Proceed using the surface check.**
2. Message: "Self-review reached the 3-round limit with one low-severity residual open … How should I proceed?" — options: *Proceed to the PR, report the residual as open*, *Run a 4th round and fix the residual*, *Stop the run here*. **Selected: Run a 4th round and fix the residual.**
3. Message: "Before enqueueing I have to name the two gaps exactly …" (head `414d900e1`) — options: *Merge now, accepting both gaps as stated*, *Re-run the local full suite first*, *Hold*. **Selected: Merge now, accepting both gaps as stated.**
4. Message: "The head moved since your last selection …" (head `66c883e51`) — options: *Merge now at this head, both gaps as stated*, *Re-run the local full suite first*, *Hold*. **Selected: Merge now at this head, both gaps as stated.**

Free-text operator messages, listed separately: "so there was at least one valid CodeRabbit review? This is enough, land without further COdeRabbit review" (twice, with "pause here" between them).

## 7. Rule check

Guard: `present` on this harness (log `.plan/temp/guard.log`). No guard refusal was recorded, and the guard log carries no line for this run's sessions; the count below is the run's own audit, not a guard-log read.

Violations of the shell rule, self-reported:
- Two shell `grep` calls during setup diagnosis: `grep -n "version" marketplace/bundles/plan-marshall/.claude-plugin/plugin.json` and `grep -n "executor_version\|0.1.2010" .plan/execute-script.py` (step 0, before any file tool was used for that question).
- Two shell `tail` calls: `tail -40` on the build-result log the build named, and `tail -5` on a test file to append after it.
No other shell file operation was issued: files were read and searched with the file tools, and the git commands were `status`, `log`, `fetch`, `merge`, `worktree remove`, `push` and one `git -C … show` (via a sub-agent).

Other notes: every script ran through `python3 .plan/execute-script.py`; builds ran through the resolved canonicals; CI through `ci`. Temp files live under `.plan/temp/`. Repository edits stayed in the worktree. Spec read: `spec_source=main_checkout`, no `spec_differ` marker (no `--spec-from-ledger` copy was requested; the epic ledger landed separately as #1867 while this run was open).

Restarts / re-dispatches: none of this session. Sub-agents: five self-review rounds (one per round), each report-only.

## 8. Build server

Setup preflight: `ready`. The routed leg **failed** for this worktree: `requested=auto, resolved=routed, mechanism=daemon_longpoll` returned `status: error`, `error: build_failed`, and the daemon child's log shows `[EXEC] pwx …` with `exit_code: -1, execution_failed` — the child could not resolve the worktree's own `./pw` wrapper and fell back to an unfindable `pwx`. The same routed command WITHOUT `--project-dir` (main checkout) succeeded, so the daemon is healthy and the worktree path is what the child cannot see. Fallback: `--execution-mode in_process` for every build, reason `routed_child_cannot_resolve_worktree_wrapper`. No `killed` job. Two bound expiries were recorded and handled by re-running with a higher explicit bound: `verify` at 1411 s (split form: unscoped `quality-gate` then `module-tests`) and `module-tests` at 2700 s on the merge head.

## 9. Residue

- **Accepted gaps at merge** (operator-selected, both named at the question): CodeRabbit's qualifying review covers `a3b6144c8`, not the final head `66c883e51` (standing authorization applied); and no local full-suite result exists at `66c883e51` — the run timed out at 2700 s, while CI's own `./pw verify` on that exact head succeeded in 1721 s.
- `test_harness_shape_guards.py`'s two tests time out (>300 s, worker starved on xdist I/O) in five consecutive local full-suite runs and pass in isolation at every head tried; CI has never reproduced it. Pre-existing, unrelated to this change, and worth a separate look at the harness scan's cost under `-n auto`.
- `create --force` re-seeds `status.json` only; a pre-existing `work/criteria-snapshot.json` survives the re-create, so a re-created plan can still be graded against a snapshot this write did not touch. Stated in the docstring now rather than implied away; behaviour is unchanged from before the plan.
- The D3 Done-when's `C9` row shape is unreachable through `run_author_verdict`'s sealing gate, so its test drives the validator seam. Documented in the test.
- `prune-local-and-remote-ref` reported `partial`: local branch deleted, remote-tracking ref already absent (the merge queue deleted the remote branch) — a no-op, not a failure.
