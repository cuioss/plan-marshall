envelope_version=1
sender_type=plan
sender_id=rb-lb-145-merge-mutex-proof-and-stuck-waiter
epic=live-blockers
kind=landing
created=2026-11-12T16:19:33Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-145-merge-mutex-proof-and-stuck-waiter
epic=live-blockers
pr=#1970
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2076
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=3
review_body_findings_handled=3
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present

# Landing — PLAN-LB-145: the merge dispatch proves the mutex, and a retained waiter is told why and how to leave

Merged as `19e909473fa9185a4ad8ac7a5e139a51f867e8e9`.

## 1. Deliverables

**D1 — `pre_merge_gate merge` refuses a plan that does not provably hold the merge mutex.** All Done-when clauses met.

| Clause | Verdict | Order | Test | Failing run | Commit |
|---|---|---|---|---|---|
| `merge()` with no lock file returns the new refusal and the runner is not called | met | test-first | `test_an_absent_lock_file_is_refused_and_nothing_dispatches` (also `test_the_refusal_code_is_the_declared_constant`) | base `4ee75be3e`, job `340d29e54930438cb7cf08826e2406b2` | `7bcc5c60a` |
| with the lock held by another plan it returns the same code naming that holder | met | test-first | `test_a_lock_held_by_another_plan_is_refused_naming_that_holder` | same job | `7bcc5c60a` |
| with an unreadable lock file it returns the refusal and not a dispatch | met | test-first | `test_an_unreadable_lock_file_is_refused_rather_than_dispatched`, `test_a_lock_file_naming_no_holder_is_refused_as_unreadable` | same job | `7bcc5c60a` |
| invocation refusal runs first (the check runs after it, before any other read) | met | test-first | `test_the_invocation_refusal_still_precedes_the_mutex_check`, `test_the_check_runs_before_the_findings_store_is_read` | same job | `7bcc5c60a` |
| holds: held-by-this-plan dispatches exactly as before, same keys | met | — (hold) | `test_a_lock_held_by_this_plan_dispatches_exactly_as_before` | green at `79827750a42845f497ad296086e07446` | `7bcc5c60a` |
| holds: findings / head / participation keep their codes and order | met | — (hold) | `test_the_findings_gate_still_refuses_a_blocking_store_behind_a_held_mutex`, `test_the_head_binding_still_refuses_behind_a_held_mutex`, `test_the_participation_gate_still_refuses_behind_a_held_mutex` | green at the same job | `7bcc5c60a` |

D1 bullet 4's decision is recorded in the PR body: **the lane's own direct enqueue is out of scope**, by the spec's default (`runbook-lane/SKILL.md` § 7 enqueues directly; `plan-orchestrator/workflow/land.md` enqueues a ledger-only PR with no plan barrier on purpose). **Executor regeneration is not owed** — no verb or flag was added.

**D2 — a waiter held behind a retained entry is told which entry, why, and how to leave.** All Done-when clauses met.

| Clause | Verdict | Order | Test | Failing run | Commit |
|---|---|---|---|---|---|
| a retained entry reports a retention reason | met | test-first | `test_a_retained_entry_names_the_git_marker_that_keeps_it` | base `4ee75be3e`, job `191aa4fce89d40dc9a6eec761cf05919` (`KeyError: 'retention'`) | `b289dbb79` |
| the next waiter's `not_fifo_front` reply names that entry and the dequeue command | met | test-first | `test_not_fifo_front_names_the_retained_entry_its_reason_and_the_exit` | base `4ee75be3e`, job `2475ccf78d084cd0a5b31953ad9741c1` (`KeyError: 'queue_front'`) | `b289dbb79` |
| holds: the same entry with no marker is pruned and the next waiter is admitted in the same attempt | met | — (hold) | `test_an_entry_with_no_marker_is_pruned_and_the_next_waiter_is_admitted` | green at the same job | `b289dbb79` |
| holds: a holder with a live worktree is still not auto-reclaimed | met | — (hold) | `test_genuine_mid_recovery_worktree_is_still_refused` (unchanged) | green | `b289dbb79` |

D2 bullet 3's decision is recorded in the PR body: **no time-based expiry**; the mid-recovery protection stays and the exit is disclosed instead.

**D3 — the documents and the pins say what the gate and the verbs do.** All Done-when clauses met.

| Clause | Verdict | Order | Test | Failing run | Commit |
|---|---|---|---|---|---|
| the doc-contract test passes on the changed documents and fails on a planted copy of the old sentence, per pinned document | met | test-first | `test_every_pin_holds_on_the_changed_document`, `test_planting_the_retired_wording_reddens_that_document_s_pins`, `test_planting_an_absence_reddens_a_wholly_new_statement` | base `4ee75be3e`, jobs `b30813a36cfa4d3b8c7522eb91c4873a` and `1f4183eae1034a7292bb552545b71692` (every pinned statement missing on both documents) | `bd01d9249`, `d1fb5c582` |

Per-head test runs: the full `module-tests` suite was green at `75c83a80c` (job `79827750a42845f497ad296086e07446`, 1164 s) and at the merged head `9ec093947` (job `55ef3f5840f6409e9ed8f5056cfd280a`, 1063 s). Scoped runs covered `pre_merge_gate` 130, `lb55_merge_head_binding` 45, the merge-lock family 144, `merge_queue_list` 22, `locks_core` 90, `build_queue` 164, `branch_cleanup` 106 and the doc-contract module 7. CI `verify / verify` was green on `75c83a80c`, `21167bfe8` and the merged head `9ec093947`.

The routed `verify` at `75c83a80c` hit the daemon's supervisory bound (1108 s, `timeout_source: explicit`); the split form — `quality-gate` and `module-tests` — is the run that is green, as § 4 of the lane prescribes.

## 2. Personas and skills

- Production code (D1, D2): `persona-implementer`, with `pm-dev-python:python-core` and `plan-marshall:ref-code-quality` as standards.
- Documentation (D3): `persona-documenter`, with `pm-plugin-development:plugin-architecture`.
- Every self-review round and every PR-comment triage: `persona-code-reviewer`.
- Per deliverable, the spec named `pm-dev-python:python-core` + `plan-marshall:ref-code-quality` (D1, D2) and `pm-plugin-development:plugin-architecture` (D3). **skills added: none** — no deliverable touched a module the spec's Expected Surface did not name.

## 3. Hypotheses

- `pre_merge_gate.merge()` runs the four existing checks and reads no merge lock — **confirmed**, `pre_merge_gate.py` L1811-1880 (the call order `_invocation_refusal` → `_findings_refusal` → `_head_binding_refusal` → `_participation_verdict` → `_findings_refusal` → `build_merge_args`).
- `queue-list` reports `not_live` exactly when `locate-plan-checkout` answers `not_found` — **confirmed**, `merge_lock.py` L1712-1719 (`_entry_liveness`).
- `holder_has_live_worktree` is true for a `.git` marker or a live plan dir under `worktrees/{holder}` — **confirmed**, `_locks_core.py` L185-248.
- A retained entry blocks every waiter as `not_fifo_front` for the budget, and `budget-reclaim` / `release --require-stale` refuse it as `holder_not_provably_dead` — **confirmed**: `holder_staleness` answers `fresh` when a worktree marker is present (`_locks_core.py` L299-301), and both recovery verbs refuse anything but `stale` (`merge_lock.py` L1818-1830, L2120).
- An entry with NO marker is pruned and the next waiter is admitted in the same attempt — **confirmed**, `merge_lock.py` L568-575 (prune inside the same read-modify-write) + L1523 (front check after it).
- `runbook-lane/SKILL.md` § 7 enqueues with `ci pr merge-queue` directly, with no mutex acquire — **confirmed**, the lane's "Enqueue and settle" block.
- The lock file records only the plan id; `release` unlinks on plan-id equality; a re-entrant `acquire` returns `already_held` — **confirmed**, `merge_lock.py` L922-941, L1935-1959, L1510-1511. The proof this plan adds is therefore a plan-id proof, and a second session of the same plan passes it (recorded in the PR body).
- `branch-cleanup.md` L101-128 is the only reader of the `admission` result and L125 admits the hazard — **confirmed**, `branch-cleanup.md` L111-127.

## 4. Findings

Self-review (three rounds, each fixed before the next):

| Round | Finding | Disposition |
|---|---|---|
| 1 | The budget-exhaustion escalation still named `blocking_plan_id` as "the entry ahead", which is the lock holder and `null` in the retained-entry shape | fixed in `662e55649` (`{front_plan}` per cause) |
| 1 | `read_lock_holder`'s `except OSError` around `Path.exists()` was unreachable | fixed in `532a678af` (read-as-existence-test) |
| 1 | Doc pins were document-wide, not section-scoped | fixed in `69e3085aa`, `d1fb5c582` |
| 1 | The L125 sentence omitted the fourth retention value | fixed in `662e55649` |
| 1 | Family test modules gained a real locator subprocess per blocked acquire | fixed in `532a678af` (fixture-level stub) |
| 2 | `queue_front.retention` / `.exit_command` were interpolated on causes whose reply carries no `queue_front` | fixed in `662e55649` (conditional block) |
| 3 | "Only one of them has a blocking plan to name" above a table where two causes name one | fixed in `75c83a80c` |

CI and PR review (CodeRabbit, one review on `75c83a80c`, three actionable inline findings):

- `finding: coderabbit inline inline-1 — 21167bfe8` — filesystem probe failures folded into `none`/absent. Fixed: `_locks_core._path_present` answers `False` only for a genuinely missing path and lets any other `OSError` propagate, so retention answers `unknown` and the prune keeps the entry. Pinned by `test_a_path_probe_that_cannot_answer_is_not_absence`.
- `finding: coderabbit inline inline-2 — 21167bfe8` — a non-UTF-8 lock file raised `UnicodeDecodeError` out of `read_lock_holder`. Fixed: `(OSError, UnicodeError)` → `unreadable`. Pinned by `test_check_reports_an_unreadable_lock_file_rather_than_raising`.
- `finding: coderabbit inline inline-3 — 21167bfe8` — the test mirrored `RETENTION_STATES` in a literal. Fixed: the expected set is derived (`RETENTION_STATES - {RETENTION_UNKNOWN}`).
- All three threads were replied to with the commit and resolved; CodeRabbit marked each "Addressed in commit 21167bf" and resolved the thread itself. `review-gate` on the merged head: 0 unresolved threads, 3/3 body findings handled.

## 5. Reviewers

| Reviewer | Required | State | Head | History |
|---|---|---|---|---|
| coderabbit | yes (`quota_limited: true`, `review_complete_after_handling: true`) | reviewed | `75c83a80c` covered (`final_review_risk_coverage: {sourceCommitId: 75c83a80c, coveredCommitId: 75c83a80c, kind: reviewed}`) | triggered `@coderabbitai review` at 13:08Z on `75c83a80c`; 3 actionable findings, all fixed and resolved at `21167bfe8`; no re-trigger owed (`review_complete_after_handling`, findings all handled); its later attempt on `21167bfe8` reported a review limit, which the exemption covers |
| sourcery | no (optional) | refused | `75c83a80c` | triggered `@sourcery-ai review` at 13:17Z; refused for its own quote ("used your own review budget of 250,000 diff characters for the last 7 days"); optional, so the merge is not gated. It ran again on `21167bfe8` and reported success but filed no comments |

Standing review authorization: coderabbit holds a qualifying review of `75c83a80c` with every finding handled, so per § 7 the currency demand does not apply to the later heads (`21167bfe8`, `9ec093947`) and no re-trigger was posted.

## 6. Operator questions

None asked. The run was never blocked and no rule needed bending. No free-text operator messages were received.

## 7. Rule check

- Guard: `present`. Its log is `.plan/temp/guard.log`; this run's session is `ses_e315c7f41ffeNmszWMBDAM6LVm`, which carries exactly **three** refusals:
  - R1 — a `grep … | head` pipe while looking for existing `import merge_lock` sites. Re-run with the Grep tool.
  - R2 — `rm` of the `test/plan-marshall/manage-locks/conftest.py` I had just created and needed gone (a local conftest shadows the root `conftest` module). Replaced with `git clean -fd -- <path>`.
  - R5 — an accidental `python3 .plan/execute-python --help` (a typo). Not repeated.
  No workaround followed any refusal; nothing was retried in a forbidden form.
- Builds: 43 routed builds, all `daemon_longpoll` (mechanism taken from each build's `[BUILD-SERVER] resolved build` line). One bound expiry (`verify`, job `0b348811d79a481ab839beb4bf3ab137`, 1108 s) — continued with the split form, never re-submitted at the same bound. No launch fault, no degraded fallback, no `killed` job.
- One build was dispatched after the base branch moved (the merge commit), and the gate was re-run on the merged tree before pushing.
- Spec read: `spec_source: ledger_worktree`, no `spec_differ` marker — the ledger worktree's copy was the one read.
- `executor-skew`: `not_applicable` (a source checkout; the executor maps this checkout's own scripts, so the lane text cannot name a verb they lack). Recorded, never asked about.
- Git: every staging was by explicit path; no `git stash`, `git restore`, `git checkout --`, `git rebase`, no forced push; the base branch was brought in by a merge commit ending with the resolved trailer; cleanup used `git worktree remove` (no force) and the sanctioned prune/switch verbs, never `git branch -D`.
- Repo files were created and edited only inside the worktree; the only `.plan/` writes are `.plan/temp/` state plus the `ci` body slots.

## 8. Build server

- Setup preflight: `ready` (`registered: true`).
- Mechanism counts: `daemon_longpoll` 43, `in_process_fallback` 0.
- Fallbacks / retries: none. One routed `verify` returned `timeout` (bound 1108 s, `timeout_source: explicit`); per § 4 the split form (`quality-gate` then `module-tests`) replaced it, and both are green.
- No `killed` job. No `runtime_stamp_reason` was reported.

## 9. Residue

- **A pre-existing, out-of-scope defect was noted while reviewing this change** and is NOT fixed here: `test/plan-marshall/manage-locks/test_manage_locks_merge_lock_live_worktree_reclaim_guard.py`'s token-failure cases claim to exercise the REAL `_set_title_token` / `_push_title_token` wrappers, but the autouse `_stub_title_tokens` fixture replaces exactly those wrappers, so those assertions are weaker than their docstrings say (this predates the plan).
- `phase-6-finalize/SKILL.md` still describes `pre_merge_gate` in its script table as findings-only; it already omitted the head binding and participation before this plan, so this change did not make it false — worth a later sweep, not this plan's.
- Sourcery did not review this PR (its own weekly quote); it is optional, so nothing is owed, but a future plan touching this code will not have had that lens.
