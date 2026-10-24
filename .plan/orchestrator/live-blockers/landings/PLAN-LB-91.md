# Landing Analysis: PLAN-LB-91 — remap rewritten commits and name the rewrite at the 5-execute boundary

epic: live-blockers
workstream: WS-01
pr: #1847 (`5a6058a6e`, base `main`, merge queue)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth.
> **(re-read)** = re-checked by the orchestrator in git, the CI abstraction, the Sonar read or the run's evidence files.
> **(landing)** = stated by the landing message and not independently reproducible here (test runs are not re-executed).
> Token usage is out of scope by the 2026-10-23 ruling and is not analysed.

## Verdict

Runbook lane, `deepseek-v4.1-flash/high`, 09:17Z first failing-run log to a 20:52Z landing (≈11.5 h) **(landing)**. Both
deliverables landed on the narrowest footprint of any plan in this epic: **7 declared entries, 7 realized, symmetric
difference 0**. Every checkable claim holds — merge sha, both guard refusals, the Sonar figure, the exact file set. The
run also carried the one thing the previous four did not: it acted on the orchestrator's collision notice and kept its
`_cmd_lifecycle.py` change confined to its own D2 region.

## Deliverable Fidelity vs Spec

| Deliverable (spec) | Verdict | Evidence |
|---|---|---|
| D1 — a rewrite is mapped onto the ledger without breaking append-only | shipped-as-specified | `manage-change-ledger` gains `remap`; `_ledger_core.py` + `manage-change-ledger.py` + `SKILL.md` in the diff **(re-read)**; emit→consume wiring in `finalize-step-sync-baseline.md` **(re-read)** |
| D2 — the refusal names the rewrite and carries the repair | shipped-as-specified | `_cmd_lifecycle.py` in the diff **(re-read)**; the tri-state `commit_ancestry` primitive and the `signature` payload **(landing)** |

Claimed `deliverables_done=2` of 2. The Done-when verdicts are the run's own, with `test-first` evidence against
`5fdec1ceb` and green runs at `bf5cee688` **(landing)**; not re-executed, per the prime directive.

**Surface — exact.** Declared 7, realized 7, `added_count=0`, `missing_count=0`, state `clean`
**(re-read: `git diff --name-only 5a6058a6e^1 5a6058a6e` + measured `surface_delta`)**. This is the first plan in the
epic whose realized footprint equals its declaration exactly — worth recording as the counter-example to PLAN-LB-44's
19-file expansion.

## Metrics and Anomalies

- Tokens: `unknown` — out of scope by the 2026-10-23 ruling; not recorded as a defect.
- Duration: ≈11.5 h (09:17Z → 20:52Z), the longest runbook run so far **(landing)**.
- Self-review: three rounds, `budget-exhausted`, one Low finding accepted by the operator at the limit **(landing)**.
- **CI flakiness, three instances:** two PR `verify` runs and one merge-group run failed on the project's mypy
  cache-freshness heuristic (`test-compile` 204/211 files/s against a 200 ceiling), not on code; reruns passed
  **(landing)**. One of them cost an operator question. Not staged (focus rule), but it is a recurring false-red class
  that will keep costing questions.
- Build server: every build `in_process` with `executor_absent_from_worktree` until 11:18Z, when the worktree executor
  appeared; `build-routing` then answered `auto` **(landing)**.

## Routing and Merge Behavior

- Review: CodeRabbit, three formal passes (`4e82c074e` 14:15:51Z, `d17106e6a` 15:32:44Z, `101253ed8` 16:38:18Z), 10
  findings, all fixed or answered with resolved threads; the post-push re-trigger at 17:59Z was refused on the rate
  window, which the standing authorization covers **(landing)**. Sourcery refused on its diff-character quota (4 d 2 h);
  optional.
- CI/merge: green on `bf5cee688`; merged through the merge queue at `5a6058a6e46b32657b466e04ee3a57e867c47fad`
  **(re-read: `ci pr view`; footprint base == that sha on `origin/main`)**. One merge-group dequeue was caused by the
  same mypy heuristic and re-run first, then merged.
- Sonar: landing carries `open_issue_count=0`, `open_issue_rules=none`; re-read against the service for PR #1847 gives
  `count_status: confirmed`, `0`, no rules **(re-read)**. Agreement.
- Guard/conduct: `guard: present`. Both disclosed refusals are in `.plan/temp/guard.log:190-191` for session
  `ses_e97f7fe8affeJaft3TAYDXIQ0u` — R5 at 16:29:18Z and 17:16:54Z, both the `execute-tool` spelling **(re-read)**, exactly
  as the landing reports them. The run also discloses read-class shell operations (`ls`, `tail`, `grep -n`, `readlink`,
  `date`) as kept-with-exception, and one **operator-authorized** write outside the lane boundary: `generate_executor.py
  generate` regenerating the main checkout's `.plan/execute-script.py` **(landing)** — that is why the executor now reads
  `0.1.1996`, and it closes the "executor surface cache predates the new verbs" residue folded on the PLAN-LB-73 landing.

## Reconciliation Actions

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-91 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-91 --field pr --value 1847`
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-91 --field landing --value landings/PLAN-LB-91.md`
- [x] row `plan_marshall_plan_id` stamped — `orchestrator queue --set-row PLAN-LB-91 --field plan_marshall_plan_id --value lb-91-change-ledger-rewrite`
- [x] epic.md narrative reconciled: the LB-43 `_cmd_lifecycle.py` overlap updated — LB-91's side is now on `main`
- [x] no defect opened for `total_tokens` (2026-10-23 ruling)
- [x] resume anchor updated — `manage-status update-field --field resume_anchor --store orchestrator`
- [x] `queue-view.md` regenerated — `orchestrator regenerate-view`

## Follow-Ups

- **The LB-43 collision is now half-realized.** `_cmd_lifecycle.py` on `main` carries LB-91's D2 refusal region; LB-43's
  worktree still holds its own uncommitted change to the same file on a base that predates it. LB-43 must rebase and
  resolve; the intended resolution, stated by both sides, is to keep LB-91's refusal logic and re-apply LB-43's change on
  top. Watch for it at LB-43's landing.
- **The lesson this plan came from (`lessons-routing-046`) is closed by the merge.** A history rewrite now remaps rows
  instead of invalidating them, and the boundary names the condition rather than reporting a bare unrecorded set.
- **The mypy cache-freshness false-red class is not staged** (focus rule) but recurred three times in one run; it belongs
  with the CI-flakiness watchers rather than in a new spec.
