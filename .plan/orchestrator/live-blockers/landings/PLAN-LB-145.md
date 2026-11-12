# Landing Analysis: PLAN-LB-145 — the merge dispatch proves the mutex, and a retained waiter is told why and how to leave

epic: live-blockers
workstream: WS-01
pr: #1970 (merge commit `19e909473fa9185a4ad8ac7a5e139a51f867e8e9`, one parent `862d6205268dfb42fef5904a58bdffd5c9743f45`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

One message from the runbook lane (sender `rb-lb-145-merge-mutex-proof-and-stuck-waiter`, revision 0, `merge_state=merged`, deliverables 3/3). It is `complete: false` on `total_tokens` alone (out of scope under the operator's focus rule, as for every runbook landing in this epic). The row was `running` and carried no `pr` or plan id; both are stamped now from the sender and the provider. The squash commit has one parent and touches 14 paths (5 under `marketplace/bundles/plan-marshall/skills/`, 9 under `test/`; read with `git show --stat 19e909473`).

The facts block agrees with ground truth: `unresolved_review_threads=0` and `review_body_findings_total=3` equal the provider's numbers from `runbook_lane review-gate --pr-number 1970` (ids `inline-1` to `inline-3`). `review_body_findings_handled=3` was re-read from the run's progress file: three coderabbit `finding:` lines (`progress.md:28-30`). The bare `review-gate` re-run reports `handled: 0` and `merge_allowed: false, reason: body_findings_undisposed` because it holds no dispositions input, which is not a difference. `sonar_open_new_issues=n/a`. The PR reads merged with `merge_commit_sha 19e909473`. One lane statement is not borne out (C3 below, the PR-body record of the plan-id proof); no false claim on a review number.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — `pre_merge_gate merge` refuses a plan that does not provably hold the merge mutex | shipped-as-specified | `_merge_lock_holder_read` `pre_merge_gate.py:1777-1793`, `_merge_lock_refusal` `:1796-1836` (re-read: three refusals under `merge_lock_not_held`, holder `{plan_id}` / `none` / `unreadable`, plan id, `dispatched: false`, remedy); called at `:1913`, after `_invocation_refusal` and before the store query, head binding and participation fetch (re-read); `branch-cleanup.md:847` states that the gate asks and the `pre_merge_only` clause (re-read); disposition `branch-cleanup.md:1671` (re-read). Tests `test_pre_merge_gate_merge_lock_proof.py` (new; `:195-213` re-read) |
| D2 — a waiter held behind a retained entry is told which entry, why, and how to leave | shipped-as-specified | `waiter_retention` `_locks_core.py:292-315` (re-read: `plan_dir` / `git_marker` / `none` / `unknown`, a raised probe answers `unknown`); `_path_present` `:185-203`; the prune, `queue-list` and `queue_front` consumers (`merge_lock.py` `:528`, `:1916`, `:1490-1516`) are leaf reads, not re-read; escalation text `branch-cleanup.md:691,717` (re-read) |
| D3 — the documents and the pins say what the gate and the verbs do | shipped-as-specified (the wording has defects, L3-3 to L3-5) | `manage-locks/SKILL.md` (leaf read, not re-read), `branch-cleanup.md:125,691,717,847,1671` (re-read); new `test_merge_lock_retention_doc_contract.py` (`:170-191` re-read) |

Spec sub-points: the lane settled every HYPOTHESIS in its report. Re-read here: the retained-entry hypothesis is confirmed in conclusion and wrong in the mechanism the lane names (L1-4); the plan-id-proof hypothesis is confirmed (L1-3); the lane's direct enqueue stays out of scope by the spec's default, so the epic's open decision (3) is not closed by this landing, only left to a later plan.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for; this was the only landing in the firing.
- **Verdict:** layer 1 findings (2 minor, 5 info); layer 2 findings (3 minor); layer 3 findings (6 minor, 7 info). No blocker and no major. The layer-3 defects are reported to the operator in the same turn; none is fixed inline.

Re-read: `pre_merge_gate.py:1775-1845,1900-1985`; `_locks_core.py:170-320`; `merge_lock.py:1685-1730,1940-1985,2225-2250`; `build_queue.py:840-870`; `branch-cleanup.md:120-130,685-725,845-848,1660-1685`; `test_pre_merge_gate_merge_lock_proof.py:195-220`; `test_merge_lock_retention_doc_contract.py:170-195`; the squash commit body; the progress file's `finding:` lines; the provider through `review-gate` and `pr view`; the changed path list through git; the surface delta through `inbox landing-check`. **Not re-read** (unverified leads): `merge_lock.py` `:528`, `:825`, `:935`, `:984-1016`, `:1117`, `:1490-1516`, `:1631-1649`, `:1786`, `:1916`; `manage-locks/SKILL.md` lines (`:533-536`, `:574-585`); `branch-cleanup.md:107`; the whole `.claude` executor `PYTHONPATH` question; the consumers' tests under a raising probe; the six added test files' content; and every conformance row except the two stated as re-read below. No leaf rule break was reported (the leaf used only `Read` and `Grep`).

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | The D1 rule "the holder must be this plan" fits every `merge_hold_window` mode: the `pre_merge_only` acquire at the Pre-Merge Gate precedes the dispatch (re-read); the other mode's release-before-wait and re-acquire-before-merge is a leaf reading, not re-read | checked (leaf; `pre_merge_only` arm re-read) | confirms | `branch-cleanup.md:847`; leaf `:107` |
| L1-2 | The D1 clause "after the invocation refusal, before any provider read" does not conflict with fail-closed, but it puts the only mutex read before the longest step and never reads the holder again before the dispatch at `:1976`, while the findings store IS re-read at `:1964` for the same time-of-check reason. The spec chose cost over currency | checked (re-read) | refutes | `pre_merge_gate.py:1913,1964,1976` |
| L1-3 | Plan-id-proof hypothesis holds: the gate compares plan ids only (`:1813`, re-read), so a second session of the same plan passes the proof; the lock file's content and the re-entrant `already_held` are leaf reads, not re-read | checked on the gate side (re-read); the lock-file side is a lead | confirms | `pre_merge_gate.py:1813`; leaf `merge_lock.py:1016,1631` |
| L1-4 | The hypothesis that `budget-reclaim` and `release --require-stale` refuse a RETAINED QUEUE ENTRY as `holder_not_provably_dead` has the wrong mechanism: both verbs act on `merge.lock`'s recorded holder only. `budget-reclaim` returns `nothing_to_reclaim` when no lock file exists, and `release --require-stale` reads `_read_holder(lock_path)` and refuses on a holder verdict other than `stale`. A retained queue entry that holds no lock is never touched by either. The conclusion stands (the only exit is `dequeue`); the lane's "confirmed" with that mechanism is a misstatement | checked (re-read) | refutes | `merge_lock.py:2239-2248,1955-1978` |
| L1-5 | Spec gap: the hazard the old `branch-cleanup.md` sentence described was an abandoned waiter whose plan directory is still in its worktree. That entry's retention is `plan_dir` and it looks live; D2's premise and the shipped disclosure centre on a `git_marker` entry. With no time-based expiry, by design, the original hazard is named (entry, `exit_command`) but nothing tells the waiter it is stuck | checked (re-read of the L125 sentence) | refutes | `branch-cleanup.md:125` |
| L1-6 | The holder vocabulary `{plan_id}` / `none` / `unreadable` collides with valid plan ids: the plan-id validator's regex `^[a-z][a-z0-9-]*$` (`_locks_core.py:254`, re-read) admits `none` and `unreadable`, so a foreign holder named `none` reads like an absent lock in the refusal payload (`pre_merge_gate.py:1819`, re-read) | checked (re-read) | refutes | `pre_merge_gate.py:1816-1823`; `_locks_core.py:254` |
| L1-7 | Every Done-when clause can fail at the base: at the base `merge()` has no lock read, so the three D1 negatives dispatch; both D2 tests need `retention` / `queue_front`, which did not exist; every D3 pin is absent from the base documents | not_shown_by_reading (leaf read of the tests; the base run itself is the lane's job ids, not re-run) | none | `test_pre_merge_gate_merge_lock_proof.py:135` |

No finding names a corpus claim of a staged spec of this epic whose verdict this run can settle on a clean mapping (the spec is the shipped one, and L1-4 is a mechanism correction on a lane statement, not a corpus claim outcome), so no re-grounding verdict is persisted.

**Layer 1 verdict:** findings — 7 (2 minor, 5 info); no major

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `pre_merge_gate.py:1777-1836,1913`; `read_lock_holder` `merge_lock.py:984-997` (leaf) | `test_pre_merge_gate_merge_lock_proof.py` (negatives, order, pass; leaf read) | see L2-2, L2-3 | checked (partly re-read) |
| D2 | `_locks_core.py:185-203,292-315`; consumers (leaf) | `test_merge_queue_list.py`, `test_manage_locks_merge_lock_live_worktree_reclaim_guard.py` (leaf read) | see L2-1 | checked (partly re-read) |
| D3 | `branch-cleanup.md:125,691,717,847,1671` (re-read) | `test_merge_lock_retention_doc_contract.py:170-191` (re-read: the plant control ends in `pytest.raises(AssertionError)` over the planted text, a real control) | none | checked (partly re-read) |

- **L2-1 (minor):** `_path_present` and its substitution into `holder_is_dead` (`_locks_core.py:182`) and `holder_has_live_worktree` (`:269`) are explained by CodeRabbit `inline-1` (lane report §4) and not by a deliverable; the swap changes failure behaviour for every consumer of the two predicates, not only for `waiter_retention`: `build_queue._prune_dead_active` (`build_queue.py:855`, re-read), the acquire path (`merge_lock.py:1694,1716`, re-read) and the rate-window claim (`merge_lock.py:825`, leaf, not re-read). The leaf reports no test covers any of those consumers under a raising probe (not re-read; only `_path_present` itself is tested). Declared surface carries none of `build_queue.py`.
- **L2-2 (minor):** the lane's table (and the PR body) marks `test_the_invocation_refusal_still_precedes_the_mutex_check` as test-first with a failing base run. The test calls `merge(strategy=None)` and asserts `strategy_required` with category `invocation` and no runner call (`test_pre_merge_gate_merge_lock_proof.py:205-213`, re-read); the spec itself lists the invocation refusal's order as a HOLD, and the base already returns that refusal. The "test-first for all non-hold clauses" statement is overstated for this row. (The PR body also says "`order` is `test-first` for all of them" above a table that marks the holds `— (hold)`.)
- **L2-3 (minor):** surface delta: declared 8, realized 14, **added 6, missing 0** (`expansion_detected`). All six are test files: `_manage_locks_merge_lock_fixtures.py`, `test_manage_locks_merge_lock_stale_reclamation.py`, `test_merge_lock_retention_doc_contract.py` (the spec said the path is named at outline), `test_lb55_merge_head_binding.py`, `test_pre_merge_gate_merge_lock_proof.py` (new), `test_pre_merge_gate_refusal_category.py`. The leaf reads each as explained (a locator stub for the new subprocess, a check-unreadable case, and autouse stubs answering "held by this plan" on the older gate suites that D1 forces); that reading is a lead, not re-read. No row running in parallel declares any of these six, so no collision is recorded.
- **Claim C3 (not borne out):** the lane says the plan-id-proof caveat (a second session of the same plan passes) is "recorded in the PR body". The squash commit body, which is the PR body (re-read in full), records the direct-enqueue scope decision, no time-based expiry, no executor regeneration and no Sonar, and says nothing about the plan-id proof or second sessions.
- **Claim C1 (partly overstated):** all 19 tests the report names exist and test what is claimed (leaf read; `test_genuine_mid_recovery_worktree_is_still_refused` is pre-existing, consistent with a hold clause).
- **Leaf finding not carried:** the leaf graded the doc-contract plant control as "red by construction" and refuting. Re-read: `:183` asserts the retired wording is absent from the shipped document, `:187` asserts the plant removed the pinned phrase, and `:190-191` asserts the checker fails on the planted text. A control that fails when the checker stops catching a plant is a control; it is not recorded as a defect.
- **Claim C4 (executor regeneration "not owed", not re-checked against the template):** no verb or flag was added (leaf), but a changed `merge_lock.py`, `_locks_core.py` or `pre_merge_gate.py` file changes the hash the executor template's per-verb surface check compares (the PLAN-LB-144 L2-2 reading, `execute-script.py.template:1387-1416`, re-read in that landing, not re-read here), so on a stale executor those scripts dispatch without pre-spawn validation. Regeneration is already owed for other plans, so this adds no new owed item; **not shown by reading** for these three scripts.

**Layer 2 verdict:** findings — 3 (all minor); claims C3 and C1/C4 recorded above

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `merge_lock.py:1694,1716`; `_locks_core.py:185-203` | the acquire's FIFO-front attempt finds the lock held by H, and `stat` of H's main plan dir or of `worktrees/H` raises a non-ENOENT `OSError` (a permission fault on an untraversable worktree directory) | the error escapes `_attempt_acquire` on every attempt: no structured `blocked` or `stale_holder_live_worktree` reply, and waiters keep getting `not_fifo_front`. Before the change the same fault read as "path absent", so the holder read as dead and was reclaimed (a possible theft). The change replaces a theft with a crash, not with a fail-closed answer, and no test covers it (re-read of the code; the base behaviour is the docstring's own statement at `_locks_core.py:188-190`) | minor |
| L3-2 | `build_queue.py:855`; `merge_lock.py:825` (leaf, not re-read) | an active build-queue entry whose stamped foreign `project_root` plan path raises `PermissionError` or `ESTALE` on `stat` | `_prune_dead_active` runs inside the read-modify-write mutator, and `holder_is_dead` now raises there instead of answering "dead": the machine-global build-queue acquire fails for every build on the host until the entry is removed by hand. Outside the declared surface (re-read for `build_queue.py:855`; the rate-window claim is a lead) | minor |
| L3-3 | `branch-cleanup.md:1671` | an operator or agent follows the `merge_lock_not_held` disposition for `holder: unreadable` | the disposition contradicts itself: "All three take the same disposition … WAIT for the mutex" then "An `unreadable` holder is a STOP … no retry can clear it". It defines `unreadable` as "the lock file exists but could not be read", while the gate also answers `unreadable` when the `merge_lock` import fails or the read raises (`pre_merge_gate.py:1788-1793`, re-read). It says "every other gate may be clean", although none of them has run when this refusal fires (re-read) | minor |
| L3-4 | `branch-cleanup.md:691,696,708` | the budget-exhaustion escalation fires on `not_fifo_front` behind a `git_marker` entry | the paragraph says that entry "will not leave on its own however long this plan waits", while the unchanged question text still says "Nothing has gone wrong — it is simply taking longer" and the recommended option is "Wait and retry"; the new line (`:717`) appears only in the description. The leaf adds that an abandoned `plan_dir` waiter, the original hazard, also never leaves while `SKILL.md:583` says any retained entry does not expire (the `SKILL.md` line is a lead, not re-read) | minor |
| L3-5 | `branch-cleanup.md:847`; `pre_merge_gate.py:1800-1803` | any reader after the change | change-history wording in documents and a docstring: "it is no longer the only net", "Until this check ran, the only reader of the mutex's admission result was prose". CLAUDE.md § Documentation Standards require the current state only. The leaf also names `SKILL.md:533-534` and a `blocked_reason` bullet (leads, not re-read), and reports that the doc-contract test pins "no longer the only net" (`:80`, not re-read) | minor |
| L3-6 | `branch-cleanup.md:717` | the operator reads the escalation prompt | the added description line shows the internal values `plan_dir`, `git_marker`, `none`, `unknown` and a CLI exit command with no plain-language gloss (re-read) | minor |
| L3-7 | `pre_merge_gate.py:1913,1976` | another session of the same plan releases the lock between the read at `:1913` and the dispatch at `:1976`, with the head read, the participation fetch and the second store read in between | the dispatch can run without the mutex; a live holder cannot be reclaimed by others, so the realistic trigger is the same-plan second session the plan-id proof already admits (re-read of the positions; the reclaim claim is the leaf's) | info |
| L3-8 | `pre_merge_gate.py:1816` | none: `read_lock_holder` never returns `held` without a non-empty holder (leaf, `merge_lock.py:995-997`, not re-read) | the `or 'unreadable'` fallback is reachable only through a stubbed seam | info |
| L3-9 | `merge_lock.py:984` (leaf, not re-read) | an unresolvable main base | `read_lock_holder` resolves the default path outside its `try`, so a `RuntimeError` escapes a function documented as three total answers; the gate catches it (`pre_merge_gate.py:1792`, re-read) and `run_check` resolves the path first, so there is no live effect today | info |
| L3-10 | `merge_lock.py:1649` (leaf, not re-read) | every non-front acquire attempt inside the bounded wait loop | `_queue_front_detail` spawns a `locate-plan-checkout` subprocess each attempt, and every reply but the last is discarded: cost only | info |
| L3-11 | `merge_lock.py:1786` (leaf, not re-read) | a blank lock file, or the transient empty window after the exclusive create | `check` now reports `unreadable` with no staleness where the base reported `held` with a stale verdict; `release --require-stale` still evicts a blank holder (`:1966-1967` re-read: holder `''` reads as not `fresh`) | info |
| L3-12 | `merge_lock.py:1515` (leaf, not re-read) | the front entry is a live waiter or the lock holder | `exit_command` is offered for every front entry; dequeuing a live waiter costs it its FIFO position, and the reply does not say the command is for a provably gone holder (`branch-cleanup.md:691`, re-read, frames it so) | info |
| L3-13 | `pre_merge_gate.py:1787` (leaf, not re-read) | production import of `merge_lock` | depends on the executor putting `manage-locks/scripts` on `sys.path`; a failure fails closed as `unreadable`; the executor's path was not read | info |

Defects from the brief that the leaf checked and found absent: the gate cannot be bypassed inside `branch-cleanup` (`build_merge_args` is called only at `:1968` after every check, re-read; the lane's direct enqueue and `land.md` stay ungated by the recorded decision); an unreadable worktree directory does not crash `acquire` through the prune (`waiter_retention` catches `OSError` and `RuntimeError` and answers `unknown`, `_locks_core.py:313-314` re-read, and the prune keeps entries that are not `none`: the prune call site `merge_lock.py:528` is a lead, not re-read). The cost is that such an entry stays queued with retention `unknown` and no expiry.

**Layer 3 not shown by reading:** L3-2's exposure on the rate-window claim; whether any other caller of `holder_is_dead` / `holder_has_live_worktree` under a raising probe changes behaviour; whether the new tests would go red at the base (only a run shows it).

**Layer 3 verdict:** findings — 13 (6 minor, 7 info); no blocker, no major

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only | deviates | `branch-cleanup.md:847`, `pre_merge_gate.py:1800-1803` (re-read); other lines are leads |
| CLAUDE.md § Documentation Standards | no version history, no timestamps | conforms | no dates, versions or changelog sections in the diffs (leaf) |
| CLAUDE.md § Documentation Standards | no duplication | deviates | the mutex-proof statement appears almost verbatim in `SKILL.md:536`, `branch-cleanup.md:847` and `:1671`; the four retention values are restated in several places (leaf; `:847`, `:1671` re-read) |
| Spec standing constraint | fail closed | conforms, one exception | the gate refuses on absent, unreadable, import failure and read exception (`pre_merge_gate.py:1786-1823`, re-read); the exception is the lock-holder liveness probe (L3-1, L3-2) |
| Spec standing constraint | one reader per concept | conforms | the gate asks `merge_lock.read_lock_holder` (`:1791`, re-read); `waiter_retention` is the one predicate behind the prune and the field (`_locks_core.py:292-315`, re-read) |
| Spec standing constraint | tests use the `PLAN_MARSHALL_HOME` fixture | deviates (nominal) | the new tests isolate through `PLAN_BASE_DIR`, the right override for the main-anchored `merge.lock` (leaf, not re-read) |
| Spec standing constraint | the PR states whether executor regeneration is owed | conforms | the PR body says "Executor regeneration is not owed" (re-read); the claim itself is C4 above |
| CLAUDE.md § Commit Trailer | exactly the plan-marshall trailer and nothing else | deviates, outside the lane's control | the squash commit ends with GitHub's `Co-authored-by` line for the human author, then the `plan-marshall` trailer (re-read) |
| persona-plan-marshall-agent | plain words in operator-facing text | deviates | `branch-cleanup.md:717` (re-read) |

## Metrics and Anomalies

- Tokens: `unknown` (the harness measured none; out of scope under the operator's focus rule).
- Duration: not reported.
- Anomalies: 43 routed builds, all through the build-server long-poll; one `verify` hit the daemon's supervisory bound (1108 s) and the split form (`quality-gate`, `module-tests`) was run instead; three guard refusals (R1, R2, R5), none worked around (all lane-reported, not re-read from `.plan/temp/guard.log`). The lane merged the moved base in before pushing (a merge commit, no rebase).

## Routing and Merge Behavior

- Review: CodeRabbit (required) reviewed once, at `75c83a80c`, with three inline findings, all fixed at `21167bfe8`, replied to and resolved (lane report §4–5). `review-gate` on the merged head: 0 unresolved threads, 3 body findings, `handled` not reproducible by the gate and re-read from the progress file as 3 of 3. Sourcery (optional) refused on its own weekly quota and filed no comments; nothing is owed. The standing authorization applied: a handled review exists, so no re-trigger was owed.
- CI/merge: `verify / verify` green on the merged head per the lane; the PR reads merged through the merge queue as a squash with one parent. No rebase conflict reported.
- Sonar: `sonar_open_new_issues=n/a`; the project does not enable Sonar and this epic ignores it. No figure measured.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-145 --status shipped`
- [x] row `pr` stamped — `1970`
- [x] row `landing` stamped — `landings/PLAN-LB-145.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-145-merge-mutex-proof-and-stuck-waiter` (the sender's `{plan}` carried as data)
- [x] epic.md narrative reconciled against the queue rows (queue annotation and Decisions entry; no Open Defect opened for the incomplete landing, because `complete: false` on `total_tokens` alone is out of scope under the operator's focus rule)
- [x] resume anchor updated and `queue-view.md` regenerated
- [x] message `rb-lb-145-merge-mutex-proof-and-stuck-waiter-001.md` archived after the persist

## Follow-Ups

- **Open decision (3) of the epic** (whether the runbook lane's direct enqueue belongs under the mutex proof): the plan decided it out of scope; it stays an operator decision for a later plan.
- **Residue of this plan, one surface** (the merge-lock verbs, the gate and their documents): L3-1 and L3-2 (the liveness probe now raising), L3-3 to L3-6 (the self-contradicting and change-history wording), L1-5 and L1-6 (the L125 gap, the `none` / `unreadable` collision), L2-1 and L2-3. No fix plan is staged without the operator word; it joins the consolidated-plan decision (4), and PLAN-LB-144's residue shares `pre_merge_gate.py` and `test_pre_merge_gate.py`.
- The lane's own residue (a pre-existing weak assertion in `test_manage_locks_merge_lock_live_worktree_reclaim_guard.py`: the autouse `_stub_title_tokens` fixture replaces the wrappers the token-failure cases claim to exercise, and the leaf could not read that case) and `phase-6-finalize/SKILL.md` describing `pre_merge_gate` as findings-only: recorded as leads on the same surface, not staged.
