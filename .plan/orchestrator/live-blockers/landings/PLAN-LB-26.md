# Landing Analysis: PLAN-LB-26 — Execute loop: triage creates fix tasks that run, a triage decision survives a re-check, and long builds have one runnable wait rule

epic: live-blockers
workstream: WS-01
pr: #1769 (https://github.com/cuioss/plan-marshall/pull/1769), merged via the merge queue as `501aeb313`
harness: **OpenCode** (OpenCode Watch quality evaluation)

> Landing record for one shipped plan. Lives at `landings/PLAN-LB-26.md`. Written by the
> `analyze` verb after verifying claims against ground truth (actual code, artifacts,
> PR state) — a pasted claim is a lead, never a fact. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the analysis and
> reconciliation contract.

Source: inbox message `lb-26-execute-loop-triage-003.md` (kind `landing`, `landing-check`
`complete: true`; surface delta `unmeasured`). Analysed adversarially per the OpenCode Watch:
every deliverable assumed missing until the merged code proved it. Checked against:

- `ci pr view --pr-number 1769`: `state: merged`, `merge_commit_sha: 501aeb313515b8c638eb6fe637f733b92bac0ca7`.
- The merged diff `3133627e8..501aeb313` (47 files, +2175/−196), read by a delegated read-only
  agent that also ran the changed test modules (1496 passed) and drove one live daemon build.
- The archived plan `archived-plans/2026-10-14-lb-26-execute-loop-triage/` (status.json, logs,
  findings, handshakes, metrics, outline, request) and the OpenCode session database
  (`~/.local/share/opencode/opencode.db`, read-only), read by a second delegated agent.
- Orchestrator spot checks of the material claims: the five finalize gates' `head_at_completion`
  (`status.json:105,141,172,188,193` = `3db65fc05`), the four later commits
  (`git log 3db65fc05^..74e6bfda7`), `pr-template.md:31-32`, `execution.md:290-310,392-400`,
  `triage.md:205-220`, `_cmd_step.py:43-49,130-147`, `_build_shared.py:381`.

## Deliverable Fidelity vs Spec

The landing claims `deliverables_done=11` of 11. Verified: **6 met, 4 partial, 1 unmet.** The
plan's own functional review graded 11/11 met at `3db65fc05` and recorded `false_self_reports=2`
(two commits whose subjects under-name their content).

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — triage's fix task accepted | met (gap) | `_tasks_core.py:94` `DELIVERABLE_ZERO_ORIGINS={'holistic','fix'}`, batch copy `_tasks_crud.py:599`; `triage.md:192,203` names `origin: fix`; tests fail at parent. Gap: validator error text unchanged — the outline narrowed the spec's "one rule … and the validator's error text" to "keep the identical error text" |
| D2 — fix task schedulable, runs first | met | `_tasks_envelope.py` `assign_envelope_at_creation`; `get` returns `envelope_id` (`_tasks_query.py:135`); fix-first sort only over dependency-met tasks (`:218`). Untested: the successful manifest `envelope_count` bump |
| D3 — owned failure not re-triaged | **partial** | No deterministic verb — a prose guard in `execution.md:293-306`; no test computes the verdict; the new-findings test passes at the parent. The guard is defeated in practice: see N1, N2 |
| D4 — one re-dispatch rule, defined hand-back field | partial | Peek exception stated (`execution.md:251,395`), but `pending_verify_steps` is absent from the termination table (`:201-209`) the spec named; the doc test is a substring check |
| D5 — module-testing task not done before its test | **partial, regression** | Hold keyed on the profile name alone (`_cmd_step.py:49,137`) whatever the tier; no leaf document passes `--verification-complete` — see N3. The spec's verify-first justification of a profile-name key is absent |
| D6 — one runnable long-build rule | partial | Bounded 300 s `running` hand-back works (observed live). But `execution.md`'s outcome table has no `running` row and no re-attach procedure; `execution.md:182` and `agents.md:170` still call the seam "the only component permitted to background a build"; the doc test cannot flag the original contradiction (vacuous). See N4 |
| D7 — unchanged re-emission keeps resolution | met (gaps) | Kept branch in `add_qgate_finding`; `QGATE_PERSIST_OK` includes the new status; test parametrized from `VALID_RESOLUTIONS`, fails at parent for all five. Gaps: no last-observed timestamp (count only); `resolution_detail` not asserted |
| D8 — opt-in reopen, `fixed` only, history | met in the store | Store/CLI/checked-add tests (a)(b)(c). Deviation: commit `050e23560` makes the phase-5 Step 11c producer pass `--reopen` (outline: "no other producer"), and the self-correction test was inverted to "stays fixed" |
| D9 — checker reports re-observations | met | `test_qgate_mechanical_rerun_reports_reobserved_counts` reads 0 / 2 / 1. Caller census not shown; `scope_creep_check` reports `finding_emitted: true` on `kept`, against its own docstring (N6) |
| D10 — documents match the store | **unmet** | Documents aligned, but the required doc test does not exist (no assertion that no doc claims reopen-without-opt-in; none that the SKILL status list equals `QGATE_PERSIST_OK`) |
| D11 — reopen-by-default pins rewritten | met | Every listed test rewritten to kept or explicit opt-in; partition fixture gained `kept` |

**Tests weakened:** none unjustified. Pre-existing test edits are D11 rewrites or follow from
cost fields now stamped at creation; no skip/xfail added, no assertion loosened. **Criteria:** the
request and outline match the spec's D1–D11 (no self-rewrite of acceptance criteria), with the
D1 and D5 narrowings and the D8 contradiction noted above.

### Four commits landed after every in-house gate

The functional review, code review and pre-push quality gate (and ci-verify, automatic-review)
are stamped at `3db65fc05`. Four commits followed (09:29–09:39) and were merged unreviewed by any
in-house gate; the orchestrator-tier phase-5 build did run at `74e6bfda` and CI plus the merge
queue were green:

- `c1042312d` — envelope-count bump after the task write. Correct; untested.
- `765836501` — cost-size vocabulary docs. Out of scope, harmless.
- `050e23560` — "own repeated failures from the pending record, reopen on refile": phase-5 build
  failures are now refiled with `--reopen`. Combined with N2 this reopens a `fixed` failure into
  a pending record with no owner, so triage allocates a second fix task — the loop D3 was meant
  to close. Untested (doc-only).
- `74e6bfda7` — no gate ledger row on a `running` hand-back. Sound by inference (the daemon child
  writes its own row); untested.

### New defects in the merged code

- **N1 (high) — a red orchestrator-tier build can skip triage.** `_build_shared.py:381` files
  build failures with `add_finding` (plan-scoped store); `execution.md:396` routes `error` into the
  triage section, whose new guard reads only `qgate list --phase 5-execute --resolution pending`
  (`:298`), finds nothing, and resumes without dispatching triage. Before #1769 the `error` row went
  straight to triage.
- **N2 (high) — the ownership field is never written.** `triage.md:213-216` resolves FIX with plain
  `manage-findings resolve … --task-number {N}`, which refuses a Q-Gate hash; `triage.md` has no
  `qgate resolve --task-number`. A reopened failure therefore has no `fix_task_number` and reads as
  new.
- **N3 (high) — `module_testing` tasks never close when their tests ran in-task.** `_cmd_step.py:137`
  holds every `module_testing` task `in_progress` with `verification_owed`; only the
  orchestrator-tier `success` row closes it. Under the `per_task` tier `next` skips it, its
  dependants block, `loop-exit-guard` reports `continue` forever. Latent in this repository (its
  `module-tests` resolves to the orchestrator tier); live in any per-task project.
- **N4 (medium) — a per-task leaf can receive `running`.** The wrapper bound is 300 s while
  `per_task` covers builds up to the 600 s ceiling; no leaf document handles `running`, exit code 0.
  Re-attaching with `build_server wait` returns the wire format without `errors[]`.
- **N5 (medium, inferred) — a fix task can join an already-passed envelope** held live by an owed
  `module_testing` task, and is then never dispatched.
- **N6 (low)** — `scope_creep_check` reports `finding_emitted: true` on a `kept` outcome.

## Metrics and Anomalies

- Tokens: **landing reports `total_tokens=0`; false.** The OpenCode database holds the real usage:
  main session 42.58M input / 165K output / 310M cache-read ($4.93), resumed session 2.14M / 25.6K
  ($0.31), plus 77 sub-agent sessions not summed. The pipeline has no OpenCode token source at
  all: every token path in `opencode_runtime.py` is a deliberate no-op because the session id is
  not exposed to the shell, although the database holding the totals is readable (epic.md
  § Non-Claude-Code Failures). Recurrence of `lessons-routing-013`/`-028`.
- Duration: 62,058 s wall (18:02 → 11:16), including ~1h25m dead time after a provider crash.
  Per-phase attribution is wrong: 5-execute 12h28m absorbs four interleaved finalize passes;
  6-finalize counts only the last pass; the quality report says 6-finalize 0 s and total 50,696 s.
- Anomalies: provider HTTP 400 crashes (08:27–09:48) killed the main session mid functional-review
  (authors ran, no verifier, round never closed); the resumed session jumped straight to push,
  triage and branch-cleanup without re-running the head-dependent steps. One harness cancellation
  (22:21). 11 fix tasks, 9 triage dispatches + 3 short-circuits, 6 finalize passes, 5 loop-backs.

## Routing and Merge Behavior

- Review: CodeRabbit filed findings fixed by TASK-28..31; at the final head CodeRabbit was
  **quota-refused** ("next review in 18 minutes") yet `review_completeness` resolved it
  `participated` from inline comments on the older head. cuioss-review-bot commented only on
  `3db65fc05` and was stale at `74e6bfda`; its documented re-trigger was never run after the 10:01
  push. Sourcery (optional) refused for size.
- Merge: under a HEAD-bound `barrier-ask-override`. **Operator-authorized** — the OpenCode
  `question` tool asked at 10:12:52Z, answer "Grant authorization" at 10:24:39Z — but the prompt was
  improvised (branch-cleanup prescribes a loop-back that re-fires the review under
  `fail_into_loopback`) and omitted CodeRabbit's quota refusal and the un-re-run in-house gates.
  CI green on both PR rounds; merge queue green (1341 s).
- Surface collisions: none observed with the running PLAN-LB-31 / PLAN-LB-39.

## OpenCode Process Grade — **C**

| Dimension | Grade | Evidence |
|-----------|-------|----------|
| Phase boundaries | partial | Scripted, ordered; deep-lane outline wrote 0 assessments and carried a pending Q-Gate finding across two boundaries; resumed session re-captured the 5-execute handshake during finalize |
| Sub-agent dispatch | pass (under-logged) | 77 real child sessions (not the Antigravity inline mode); phase-5 re-dispatches skipped `effort resolve-target` (1 resolve vs 29 dispatches), so the retrospective's dispatch audit saw "0 dispatched" |
| Executor use | partial | 716 of 775 orchestrator shell calls via the executor; a `python3 -c` file read, direct `.plan/marshal.json` / `request.md` reads, grep of build logs |
| Builds | pass / **fail at pushed head** | Resolved via architecture; but finalize gates never ran at the merged head (`lessons-routing-016` recurrence) |
| CI abstraction | pass | No `gh`/`glab` |
| Findings triage | partial | 0 pending at finalize; the 5 `taken_into_account` test failures were legitimate (D11-owned pins, later green); defects: quality-gate failures auto-closed by a compile run, a false scope-creep rationale, code-review findings closed with a functional-review reason |
| Merge | partial | Operator-authorized, improvised prompt, incomplete gap description |
| Landing facts / metrics | fail | Tokens 0 against real usage; steps `done` without head binding; residue calls optional sourcery "required" and omits the CodeRabbit refusal |
| Criteria integrity | pass | Request, outline and spec agree; no self-rewrite |
| Other | fail | The plan session wrote the orchestrator ledger (transition, anchor, view, raw `git commit` in the ledger worktree) against the spec's Write-Boundary; per-deliverable commit discipline broken (D1–D3 and D4–D9 bundled under single-deliverable subjects); PR body carries the forbidden "Generated by plan-finalize skill" footer (template defect) |

Strong on mechanics, failed at the end-of-run integrity the evaluation exists to test: it merged
a head none of its own gates had seen and reported 11/11 against 6 met.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-26 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-26 --field pr --value 1769`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-26 --field landing --value landings/PLAN-LB-26.md`
- [x] row `plan_marshall_plan_id` stamped — already `lb-26-execute-loop-triage`; re-stamped
- [x] epic.md narrative reconciled — OpenCode Watch updated (1 of 3 graded), Open Defects added and recurrences recorded, queue annotations for PLAN-LB-42/44 (LB-26 landed)
- [x] PLAN-LB-47 staged for the regressions (N1–N4, D10, D4, D6 documents)
- [x] resume anchor updated; `queue-view.md` regenerated and committed

## Follow-Ups

- **PLAN-LB-47 lb-26-regression-fixes** (staged, high priority): N1, N2, N3, N4, the D10 doc test,
  the D4 termination-table row, the D6 document contradiction, N6, and the PR-template footer.
- The head-dependent-gate gap at merge (`lessons-routing-016` recurrence, process defect "no resume
  guard for head-dependent steps") is PLAN-LB-39's (running) — recorded on its Open Defect.
- OpenCode token source (`opencode.db` `session_v2`) — evidence for PLAN-LB-39 D5 / PLAN-LB-45;
  recorded on the zero-token Open Defect.
- Review barrier counts a current-head quota refusal as `participated` (inline comments carry no
  `commit_id`) — new Open Defect, nearest owner PLAN-LB-46.
- Compile run auto-closes quality-gate failures; metrics re-entry accounting; `emit-landing` before
  `archive-plan`; dispatch audit blind to OpenCode sub-agents — new Open Defects, unowned.
- Operator decision: re-review TASK-28..31 (`c1042312d..74e6bfda7`), which no in-house gate saw.
  PLAN-LB-47's scope covers `050e23560`'s interaction; the other three were judged sound.
