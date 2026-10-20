# Landing Analysis: PLAN-LB-77 — The integrity record cannot be lost and the re-freeze authorization is read and committed under one guard

epic: live-blockers
workstream: WS-03
pr: #1826 (merge commit `4eb58fbc18deb73bad07fd0bf6aa6ef70df3324d`; supersedes #1825, closed unmerged at `ca205b0b9`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying the landing message
> against ground truth: the merged diff and tree at `4eb58fbc1`, the PR through the `ci` abstraction, the run's
> progress file and the guard log, and the OpenCode session store read-only. Two read-only
> `execution-context-level-5` agents corroborated (code and tests; PR, CI and transcript); the orchestrator
> re-read `_status_core.py`, `authorize_refreeze`, the create seed, the PR comment history, and three commit
> messages itself.

## Verdict

**Grade B−.** All three deliverables are met against the spec's own Done-when text, and no test is vacuous.
The Objective is fully met, which PLAN-LB-76's was not. The grade is held
down by the process: the landing's rule check is false ("No other section-1 rule was broken by me or the
sub-agents"), the `test-compile` table hides one red pushed head and omits another, the operator was
asked a merge question containing false timestamps, a bot finding on the final head was never read, and
the code carries eight small defects that PLAN-LB-82 owns.

Lane text loaded: the PLAN-LB-72 text (`cf28a05db`), read once at 06:41:08Z from the installed OpenCode copy
(content equal to `cf28a05db` apart from two harness substitutions). It was **not** re-read after the 08:52:14Z server restart.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — a status writer cannot overwrite the integrity record | shipped-as-specified | The carry runs inside the guard (`_status_core.py:199-210`, `_carry_protected_keys` `:221-242`, read by the orchestrator); the membership is single-sourced in `_criteria_snapshot.py:122`. All three Done-when clauses fail against the pre-image and pass. Choice recorded: carry-forward, not merge. The `write_status` population is 16 calls in `manage-status/scripts/` (corroborated) plus a 17th the run missed at `orchestrator.py:6454`; the seam covers it, the docstring and test docstring do not name it. |
| D2 — authorization read, checked and committed under one guard; logs only on commit | shipped-modified | `authorize_change` takes the snapshot guard first (`_criteria_snapshot.py:968-982`) and logs after the commit; all three Done-when clauses fail on the pre-image. The spec body also said `authorize_refreeze` "gets the same treatment": only the log-after-commit half was applied, it still takes no snapshot guard (`:303-393`, read by the orchestrator). Lock order is snapshot guard then status guard everywhere. |
| D3 — matching, protection, rollback | shipped-as-specified | `_graded_status` skips a row with a parseable `criterion_id` (`:1299-1304`); the protected set is exactly `{criteria_integrity, functional_review_override_heads}` (`_status_query.py:78`); no reader of a top-level `snapshot_frozen` exists in the bundles; rollback goes through `file_ops.atomic_write_bytes` (`:1566-1592`). Two of the four rows are weakly tested, below. |
| Added-unplanned | — | `file_ops.atomic_write_bytes` and the delegating `atomic_write_file`, `test_file_ops.py`, `manage-status/SKILL.md:364`, `functional-review.md:90`, `review-rubric.md:42`, the `criteria-authorize` docstring. All are consequences of D2/D3, none is scope creep, but they sit outside the declared Expected Surface (the surface was under-declared, as in every earlier landing in this lane). |

### Tests

None is vacuous: each named test fails against the pre-image (read from the code, not from the report), none mocks away its unit.
Weak points the run did not disclose:

- `test_a_deliverable_qualified_id_refused_by_the_id_arm_does_not_match_by_text` uses `D1.C2`, which the id arm refuses by position, so it duplicates the bare-`C2` test; the branch the clause names (an id naming another deliverable, `:1266-1267`) is not exercised.
- `test_a_failure_injected_during_the_rollback_write_keeps_the_prior_bytes` sabotages `Path.open`, which the fixed path never calls: it is a tripwire against a regression to `write_bytes`, and a raw `os.write` regression evades it (the landing admits that one). No test injects a failure into the atomic restore and then checks the snapshot; the primitive alone is failure-injected in `test_file_ops.py:149`.
- `test_a_refreeze_landing_before_the_guard_is_not_reverted`: under the fix only the `snapshot_busy` arm runs, so the success-arm assertions are dead.
- `test_the_protected_set_is_exactly_the_keys_a_verb_writes` pins a constant, duplicates `lb74:35`, and checks no writer.
- The conditional rollback at the `write_snapshot` site (`:792`) and the `restored` and `NOT withdrawn` outcomes are untested.
- D1's second clause names `loop-back close` while `mark-step-done` waits; the test drives `_record_override_head` and the seam in sequence. Adequate, not literal.

### Order labels

`test-first` is **true as an order** for all rows: the tests were written, run red (logs `072833`, `075526`, `081151`), then the fix edited (first fix edit after each red run). Labels that are wrong:

- the failing runs are attributed to `da0b3ce04` for every row; D2's ran at `658ba92ea` plus the new test, D3's at `1d104b711` plus the new tests (the code under test is equivalent, the label is not);
- the D1-D3 tests were rewritten after their fixes (rollback sabotage moved `write_bytes` → `write_text` → `Path.open`; `test_a_failed_replace_leaves_the_prior_bytes_untouched` was added after the fix and was never seen failing), and the final versions were never run against unfixed code.

## Code defects (PLAN-LB-82)

Confirmed by reading; the orchestrator re-read DF1-DF3.

- **DF1** (minor): `create --force` over an existing plan now inherits that plan's `criteria_integrity` and `functional_review_override_heads`, because the create seed commits through `write_status` (`_cmd_lifecycle.py:1204`) and the live value wins. The docstring "their absence is never an intentional clear" is false for this caller. An inherited override head makes `_review_closed_reason` report the new plan's criteria closed.
- **DF2** (minor): an in-guard read that fails transiently comes back as `{}` and `_carry_protected_keys` then **pops** both keys from the caller's copy (`_status_core.py:229-242`); the old code wrote the caller's copy intact. Fail-open on the integrity binding.
- **DF3** (minor): `authorize_refreeze` takes no snapshot guard and commits before its log line (`:303-393`); a concurrent `write_snapshot` can consume an authorization whose decision line is never written. The spec asked for the same treatment as `authorize_change`.
- **DF4** (minor): the refreeze withdrawal is conditioned only on the value being `True`, so a newer, logged authorization is withdrawn by an older failing log.
- **DF5** (minor, added after the last self-review): the `kept` outcome (`:1084-1094`) leaves an authorization with no decision-log line standing, which `criteria_drift` and `open_criteria` honour. The previous behaviour left a `tampered` state, which fails closed. It contradicts `review-rubric.md:42`.
- **DF6** (minor): `verdict_row_matches` still accepts id-bearing rows by text while `_graded_status` skips them; the validator is silent where the gate leaves a criterion open. Fails closed but gives the reviewer nothing actionable. The landing lists it as a follow-up.
- **DF7** (minor, plausible): the `expected=` ownership check is compare-then-replace in two steps.
- **DF8** (minor, pre-existing): `atomic_write_bytes` has no fsync, replaces the target's mode with 0600, and leaks the descriptor if `os.fdopen` raises.
- Also: the `authorize_change` docstring (`:957-959`) says a failed log rolls the authorization back, which `kept` and `inconsistent` contradict; the follow-up `manage-config/scripts/_cmd_finalize_steps.py:301` still writes the whole status document unguarded (corroborated, read at `:273` and `:301`); and `platform-runtime/scripts/claude_runtime.py:1509` writes the archived status only (no consequence).

## Metrics and Anomalies

- Tokens (from `session_v2`, the landing says `unknown`): main session input 1,888,422 / output 87,387 / reasoning 68,618 / cache-read 86,583,808, cost $0.637; sub-agent session input 319,237 / output 24,321 / reasoning 97,637 / cache-read 16,489,728, cost $0.171. Total input 2,207,659, output 111,708, reasoning 166,255, cache-read 103,073,536; **$0.807**. Every assistant message (343 main, 94 sub-agent) is `deepseek-v4.1-flash` variant `high`, provider opencode-go; the model never changed. OpenCode 2.0.32 at the main session's creation, 2.1.0 at the sub-agent's.
- Duration: 11 h 00 m (06:41:08Z-17:41:30Z). CI and bot waits 4 h 59 m, builds 2 h 05 m, sub-agent 1 h 24 m, operator waits 44 m, merge queue 39 m, other 1 h 08 m. One session restart (08:52:14Z, it cancelled a running `test-compile`), no compaction.
- $0.81 is about a fifth of PLAN-LB-45's $3.78 for a delivery that is fully met; wall-clock is dominated by the review apparatus, not the model.
- Merge time: the merge-group commit is stamped 17:01:34Z; the PR merged between 17:38:45Z and 17:40:06Z, and the landing was written one minute later, 17:41:17Z (the orchestrator's brief had assumed 40 minutes; that was the commit time read as the merge time).

## Routing and Merge Behavior

- **Reviewers** (all times UTC): cuioss-review-bot is `quota_limited=false`. #1825: `/review` 11:09:24, guides 11:10-11:11, formal COMMENTED review 11:11:53 with one inline false positive at `file_ops.py:1590` (the `raise` is at `:1592`), answered and resolved 11:33. #1826: `/review` at 14:47:40, 14:58:08, 15:33:00, 15:56:03 and **16:24:16** (five; the landing names four and omits the last); "Failed to generate code suggestions" 14:49:06 (the Review workflow failed on `ca205b0b9` and never ran again); guides 15:57:26 and 15:57:50, "No major issues"; both **updated to head `171f9c359` at 16:25:39/40** and the Reviewer Guide then flagged "Swallowed Exception" in `atomic_write_bytes`: a false positive (the snippet it quotes contains the `raise`) that repeats the earlier one, was never read by the run, and is unanswered. No formal review exists on #1826, so the landing's "no review on the merge head" is true at review level and misleading at comment level.
- coderabbit: formal reviews 14:54:03 (`ca205b0b9`, 1 finding, fixed `0905b2082`, thread resolved) and 16:06:46 (`06610bd7`, two outside-diff findings, fixed `171f9c359`, answered by the 16:23:56 comment); both reviews were automatic after a push, each manual trigger answered "Already reviewed the last commit". Refusals: #1825 auto 11:08:57 (omitted by the landing), 11:10:40, 12:42:24, 14:15:26; #1826 14:58:39 and 16:25:09 (plus the 16:25:07 automatic rate limit on the `06610bd7`→`171f9c359` range).
- sourcery: **no `@sourcery-ai review` was ever posted on #1826**; the landing's "`@sourcery-ai review` at 14:47, refused" is the automatic refusal on PR open (14:47:29), before the run's first comment. On #1825 one manual trigger (11:11:23) was refused. Optional; no gate.
- **90-minute floor**: between 11:10:40 and 12:42:08 (91 m 28 s) and 12:42:24 and 14:15:09 (92 m 45 s) the floor held. The 14:15:26 refusal was followed by close and reopen at 14:46:52 and `@coderabbitai review` at 14:47:56, **32 m 30 s later, 57 m 30 s short**. The lane's text applies the floor only while no qualifying review exists, which was true then. The close-and-reopen came after 2 of the policy's up-to-10 re-triggers; it produced a review within 7 minutes. The later triggers (14:58:20 four minutes after a qualifying review; 15:56:15; 16:24:48, 86 m 09 s after the 14:58:39 refusal) fall under the standing authorization, not the floor.
- **Standing authorization at `171f9c359`** (lane §7): conditions 1-3 met (qualifying reviews on `ca205b0b9` and `06610bd7`; both findings handled; re-triggered once after the last push and refused 16:25:09). Condition 4, every other gate green on the current head: cuioss-review-bot has no formal review at any head; it was covered by the operator's 15:49:04 selection, made at head `0905b2082`, and the run enqueued two heads later without asking again and without reading the 16:25:39 guide update. Whether the selection stretches to cover those heads is a ruling for the operator; the orchestrator does not treat it as a settled break.
- CI: checks at `171f9c359` all SUCCESS (verify 1,600 s, gate, conclusion, CodeRabbit, generate-check, dependency-review, Sourcery-without-a-review); merge-group run 39464195820 succeeded. The cuioss-review check is absent after `ca205b0b9`.
- PR body and squash message are stale: they cite `quality-gate`, `test-compile`, `module-tests` (31,459 tests) at `ca205b0b9`; the final head's run is 31,522. The squash message also carries the CodeRabbit summary and an extra `Co-authored-by: cuioss oliver` line.

## Operator questions (rebuilt from the transcript)

Exactly two, both completed; no aborted question; no free-text message besides the first prompt.

1. 06:42:30Z, header "Missing spec", options Abort / Run PLAN-LB-74 / Run PLAN-LB-75. Answered 07:23:43Z with the free text "ledger landed", none of the options; the run re-read and proceeded. The question's claim "a repo-wide search finds no LB-77" came from globs that ignore dot-directories (the run noted this itself); the directory listings do show the spec was absent until the ledger landed.
2. 15:46:25Z, header "Required reviewer missing", options Keep retrying / Close and reopen the PR again / Merge without the cuioss review, on my authority. Selected the third at 15:49:04Z. The question named "three `/review` triggers (14:58Z, 15:04Z, 15:05Z)"; the real ones were 14:47:40, 14:58:08 and 15:33:00. **15:04Z and 15:05Z do not exist.** The premise "no review at any head of #1826" was true at 15:46:25Z and became false at comment level at 15:57:26Z. The question also cited 31,459 tests, true at `0905b2082`.

## Process findings

- **Lane text**: PLAN-LB-72 text (`cf28a05db`), loaded once, not re-read after the 08:52 restart. The run resumed from the progress file alone.
- **Skills and personas**: the main session tried seven colon-notation ids at 07:24:48 (all failed) and loaded the flat ids at 07:24:54-57 (implementer, three domain skills, ref-code-quality, pytest-testing, module-tester, plugin-architecture); `persona-documenter` and `persona-code-reviewer` were loaded in the main session at 09:45:51 and PR triage ran with the reviewer persona loaded. The sub-agent loaded `persona-code-reviewer` at 09:08:23. Landing §2 matches. Skills were loaded once for the three deliverables.
- **Self-review**: three dispatches to one sub-agent session (09:08-09:45, 10:04-10:22, 10:30-10:59), 15 / 6 / 0 findings, CLEAR at head `ca205b0b9`. No fourth dispatch. `self-review: clear` in the fact block covers only that head: **`0905b2082`, `06610bd71` and `171f9c359` were never self-reviewed**, and `171f9c359` carries new logic (`expected=`, `kept`) that is the source of DF5 and DF7.
- **Section-1 hand-off to the sub-agent was abridged** (lane §5 says verbatim): "There is no session budget" is missing, three rules are shortened and the `--execution-mode in_process` build form is absent.
- **Sub-agent daemon builds**: 17 `pyproject_build run --command-args "module-tests …"` builds from the worktree without `--execution-mode in_process` (routed through the daemon) plus three `build_server wait` calls, 09:12:54-10:56:07, two in parallel at 09:20:39. The lane text says "Never use the daemon" and runs executor calls from the main checkout; it does not literally forbid sub-agent builds, and §5 says the sub-agent's breaks count as the main session's. The daemon coalesced results ("the sibling job's 57") and one whole-bundle run hit the daemon's 483 s bound. This is the build-server behaviour PLAN-LB-78 is about, seen from the other side: the operator wants the lane on the build server, and the lane text says the opposite.
- **Main session shell**: of 194 shell calls the only shell file operation is `wc -l .plan/temp/guard.log` (17:40:35, admitted). No compound commands, no `git grep`. The one `git ls-files 'test/**/*lb74*'` is the sub-agent's (09:23:18).
- **Commit trailer**: all eight non-merge commits carry exactly `Co-Authored-By: plan-marshall <noreply@cuioss.de>`; the merge commit `06610bd71` carries **no trailer** (read by the orchestrator).
- **Guard log**: `.plan/temp/guard.log` has no line for either session id (last line 07:24:24Z). The worktree has been removed, so a worktree-local log could not be inspected.
- **Mislabels**: progress line 40 calls `0905b2082` "D4/refactor" (the spec has three deliverables; the commit subject says D1, D3).

### `test-compile` at every pushed head

The pushed heads (from the push windows) and the evidence:

| Head | Verified result |
|------|-----------------|
| `658ba92ea` | no run |
| `1d104b711` | no run |
| `be7937fd6` | **ran at the clean head 08:40:52-08:42:37 (log `084118`) and FAILED** (mypy, `test_lb77_authorize_guard_d2.py:142`); fixed by `b7c478b03`. The landing says "pushed without a `test-compile` run at that head"; the progress file has no line for the red run |
| `b7c478b03` | success (`085238`) |
| `125617b3d` | **pushed 10:04:07Z, no run; absent from the landing's table and its deviation sentence** |
| `ca205b0b9` | success (`105958`) |
| `0905b2082` | success (`154046`, 15:40:36; the progress file has no line for it, the landing's table is right) |
| `06610bd71` | success (`155011`) |
| `171f9c359` | success (`165323`) |

Heads without a verified green `test-compile`: `658ba92ea`, `1d104b711`, `be7937fd6` (red), `125617b3d`. The landing names three and mischaracterises one.

## Landing-message accuracy

Correct: PR number and merge sha; #1825 closed unmerged; every deliverable verdict; both questions' options and answers; the four-model list; the 16 call sites (count); the three self-review round counts; both CodeRabbit finding sets and their fixes; the CodeRabbit refusal times; the residue list; cleanup done.

False or misleading:

1. §7 "No other section-1 rule was broken by me or the sub-agents": the sub-agent ran 17 daemon builds, the merge commit has no trailer, `125617b3d` and the red `be7937fd6` are misreported, the lane was not re-read after the restart, the abridged hand-off.
2. §1 table: `be7937fd6` "pushed without test-compile" (it was red); `125617b3d` omitted.
3. §1 order column: every failing run attributed to `da0b3ce04`; D2 and D3 ran at `658ba92ea`/`1d104b711` plus tests.
4. §5 "`/review` at 14:47, 14:58, 15:33, 15:56": a fifth at 16:24:16 omitted; "no review on the merge head" omits the 16:25:39 guide update and its unanswered focus area.
5. §5 sourcery "`@sourcery-ai review` at 14:47, refused": automatic refusal, never triggered on #1826.
6. §5 the 90-minute history is not stated; the 14:47 re-trigger was 32 minutes after a refusal.
7. §6 question 2's "no review at any head" is stated without the false timestamps the question carried.
8. Facts block: `model=deepseek-v4.1-flash` without the variant (the lane's fence requires every model and variant); `effort`, `plugin_version`, `total_tokens` absent; `self-review:clear` for one head of four.
9. §3 "all 16 write_status call sites" is a count of one directory; the 17th caller is outside it.
10. `landing-check`: `complete: false`, `missing_keys` = `total_tokens, effort, plugin_version` — the recurrence of the PLAN-LB-78 D3 defect, not a new one. The fence at `cf28a05db` §8 lists only schema, plan_id, epic, pr, merge_state, cleanup_owed, deliverables_total, deliverables_done, total_tokens, harness, model and steps.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-77 --status shipped`
- [x] row `pr` stamped — `1826`
- [x] row `landing` stamped — `landings/PLAN-LB-77.md`
- [x] row `plan_marshall_plan_id` stamped — `lb-77-lb-74-completion` (from the sender `rb-lb-77-lb-74-completion`)
- [x] `epic.md`: grade table and watch lists, the integrity-record defect entry, the harness-install watch, the incomplete-landing defect recurrence, a build-server coalescing watch, a standing-authorization ruling
- [x] PLAN-LB-82 staged (`lb-77-completion`, medium, WS-03, runbook lane) and its Expected Surface verified with `corpus surfaces`
- [x] PLAN-LB-69 gains the datapoints below; PLAN-LB-78 gains the build-server coalescing claim
- [x] resume anchor rewritten; `queue-view.md` regenerated

## Follow-Ups

- PLAN-LB-82 owns DF1-DF8, the `authorize_refreeze` guard, the tests listed above, the `manage-config` unguarded writer and the validator mismatch.
- PLAN-LB-69 (landing audit): a failing gate the progress file does not record (`be7937fd6`) and a pushed head the table omits (`125617b3d`) mean the audit must cross-check the head list against the build logs, not against either document; and a question that quotes timestamps must be checked against the PR.
- PLAN-LB-78: the daemon's coalescing and 483 s bound are evidence for how the lane should serialise its builds.
- Ruling for the operator: does a merge-without-reviewer selection made at one head cover the heads pushed after it?
