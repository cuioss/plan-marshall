envelope_version=1
sender_type=plan
sender_id=oc-lb-63-lb-60-completion
epic=live-blockers
kind=landing
created=2026-10-17T20:12:16Z

```landing-facts
schema=landing-facts/1
plan_id=oc-lb-63-lb-60-completion
epic=live-blockers
pr=#1795
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
```

# Landing report — PLAN-LB-63 (dead-step cleanup never deletes on a partial scan; the upgrade recovers from an executor that fails to import)

PR #1795 merged as `b90e8a25f981f71c90e84364af32f01aa40f02a1`.

## 1. Deliverables

**D1 — a partial scan is `unknown`, and an unknown sweep says so.** Commit `a35c7e9ca`; review fix `a57d9578e`.

- *"a fixture phase-6 skill directory without `workflow/` yields `unknown` for `default:push` and deletes nothing"* — **MET**. `test_partial_phase6_dir_without_workflow_leaves_the_surface_unresolved` (red `-070335`: `assert True is False`; green `-071146`) and `test_sync_defaults_partial_phase6_scan_keeps_steps_and_reports_unknown_sweep` (red `-070335`: the live step was deleted, `assert 'default:push' in {}`; green `-071146`).
- *"an unresolved sweep reports `dead_sweep: unknown`"* — **MET**. `test_sync_defaults_unresolved_discovery_deletes_no_step` (red `-070832`: `KeyError: 'dead_sweep'`; green `-071342`).
- *"a genuinely dead id's removal record carries its params and a `dead_step` origin"* — **MET**. `test_sync_defaults_dead_default_id_removal_record_carries_params_and_dead_step_origin` (red `-070733`; green `-071240`), with the back-fill consequence pinned by `test_sync_defaults_dead_removed_id_later_backfill_does_not_read_as_operator_removal`.

**D2 — the upgrade recovers from an executor that fails to import.** Commit `28f2baf27`; review fix `df3459452`.

- *"a test with an executor fixture whose import raises `ModuleNotFoundError` reaches the stage plan after regeneration; it fails at `9d4207dcc`"* — **MET**. `test_plan_recovers_from_an_executor_that_fails_to_import` (red `-072703`: `assert 'fresh' == 'regenerated'`; green `-073219`) and `test_bootstrap_import_failing_executor_recovers_without_consent` (red `-072501`; green `-073115`). The red was observed on the branch base `f77ff76b5`, whose production files are byte-identical to `9d4207dcc` (`git diff --stat 9d4207dcc f77ff76b5 -- <the three production files>` is empty).

## 2. Hypotheses

- **HYPOTHESIS (D2): "the import failure can be probed without executing the executor's code path that fails" — CONFIRMED.** `templates/execute-script.py.template:1687-1691` handles `--list` in `main()` before any notation resolution or dispatch, while the module-level bootstrap import block (`:274-311`) runs on every invocation; a failed import with an unresolved bootstrap directory prints `execute-script.py cannot start:` and exits (`:252-265`), otherwise the `ImportError` propagates as a traceback. Both are observable from `python3 <executor> --list`.
- The spec's OBSERVED claims held: `_implementor_scan_surfaces_resolve` was `is_dir()`-only for phase 6, dead ids were written to the operator `removed_steps` list, and `needs_recovery = executor_version is None`.

## 3. Findings

- **Self-review round 1** — all four Done-when clauses met with validated red-first evidence; no removed/relaxed assertions; no docs made false; three entailed files (`_config_defaults.py`, `_config_core.py`, `test_config_defaults.py`), `_cmd_quality_phases.py` untouched. Eight risks dispositioned without a change (probe reachability, hard-coded `python3`, marker classification, the ungated recovery, probe cost, `dead_sweep` with zero ids, `dead_removed_steps` accumulation, probe cwd).
- **Self-review round 2** — all four clauses re-verified; ten round-1 dispositions confirmed; **O2** fixed (five `warning`-semantics spots were made false by the new import-failure warning), **O3** fixed (the probe promised "Never raises" while `UnicodeDecodeError` escaped), **O1** documented as the explicit marker boundary, **O5** recorded (red-base equivalence), O4/O6 accepted as-is. Commit `5f6ea9940`.
- **Self-review round 3** (the round limit) — all fixes verified, no other false doc / relaxed assertion / unexplained file. Two residuals: the reworded `warning` enumerations name two of the three warning kinds the verb can emit (an under-claim that pre-dates the change), and the PLAN-LB-62 note belonged in the PR. The operator chose to proceed to the PR.
- **CI** — green on every head (`dc`, `5f6ea9940`, `df3459452`, `520d4938b`); `verify` green locally on each (`31120` → `31123` → `31138` tests after the main merge).
- **PR comments** — CodeRabbit's two inline comments (undecodable step docs; the startup-marker prefix) were valid: fixed in `a57d9578e` and `df3459452`, replied per thread, and both threads resolved (CodeRabbit itself marked them "Addressed" and "Review thread resolved"). The remaining comments are the bots' informational guides and rate-limit notices; `sourcery` was rate-limited (optional).
- **PLAN-LB-62** — landed (`bd8ff3236` is an ancestor of `main`); its R5 allow-list ships at `skills/platform-runtime/standards/r5-allowlist.json` and admits the documented recovery entry, so the doc form stayed unchanged.

## 4. Reviewers

- **cuioss-review-bot** — reviewed the **current head** `520d4938b` ("Code review updated until commit 520d4938b…"; tests present, no major issues, no security concerns). It also reviewed `5f6ea9940` and `df9452`.
- **coderabbit** — reviewed `5f6ea9940` (state COMMENTED, "review finished", merge risk **Low**, 2 actionable comments); after the fixes it read and confirmed the delta in its threads ("✅ Addressed in commits a57d957 to df34594") and resolved both. It did **not** formally review `df3459452` or `520d4938b`: its quota was exhausted and **six** triggers were refused (09:31, 11:33, 13:05, 14:47, 16:56, 18:32, 19:20 — only the 16:29 attempt succeeded), with stated ETAs (3/37/7/33/17 min) repeatedly wrong and two 90-minute waits still refused.
- **sourcery** (optional) — refused: own review budget exhausted ("next in ~2 days").

## 5. Operator questions

1. *Self-review round limit — how to proceed?* Options: proceed-to-PR / round 4 / widen-only. Selected: **"Proceed to the PR"**.
2. *CodeRabbit has not reviewed the current head (`df3459452`) — how to proceed?* Options: continue-waiting-6-10 / park-and-resume / close-and-reopen. Merging without a current-head CodeRabbit review was stated as a rule break and not offered. Selected (free text): **"If there was at least one review of CodeReabit: Merge and contniue"** — the condition holds (CodeRabbit reviewed `5f6ea9940` and verified the delta fixes in its now-resolved threads), so the merge proceeded on that authorisation.

## 6. Rule check

- `guard.log` has exactly **one** line for this run: the round-1 self-review subagent's shell `ls .plan/local/plans/NO_PLAN/build-results/plan-marshall/ | tail -60` (R1, session `ses_eb721c4f1ffejiFjJW5CJ4g0wG`, `2026-10-17T08:05:20.286Z`) — a file-listing through the shell, which §5 counts as the run's. My own commands produced no guard line.
- Disclosed, rule-directed or minor non-listed operations: PR/comment/reply bodies were written to the paths the `ci prepare-*` verbs allocate under `.plan/local/plans/NO_PLAN/work/ci-bodies/` (as Steps 6–7 direct — outside `.plan/temp/`, the only other `.plan/` write besides the landing message); `git worktree remove --force` (the plain form refused on the worktree's pre-existing, never-committed `uv.lock` churn); and a manual `git fetch` + `git merge --ff-only origin/main` to complete cleanup step 3 after `switch-and-pull` refused on a concurrent session's uncommitted files.

## 7. Residue

- **CodeRabbit has not formally reviewed the final head `520d4938b`.** The merge proceeded under the operator's explicit authorisation above; its last formal review covers `5f6ea9940` (Low merge risk) and both of its comments were fixed and thread-resolved.
- The **main checkout still carries a concurrent session's uncommitted edits** — a `lane` row field added to `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_orchestrator_ledger.py` and `.../plan-orchestrator/scripts/orchestrator.py`. They were left untouched (investigated, not mine); the checkout fast-forwarded to `b90e8a25f` around them.
- A post-merge whole-tree run first hit the executor's **learned timeout** (cut at 698 s, no test failure) and passed on re-run with `--timeout 1800`.
- The two accepted self-review residuals: the `warning` enumerations under-name a third warning kind (a pre-existing under-claim), and the self-review subagents ran on the harness-default general agent (their model was not recorded).
