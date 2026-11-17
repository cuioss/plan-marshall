envelope_version=1
sender_type=plan
sender_id=rb-lb-154-conflicting-baseline-drift-recovery
epic=live-blockers
kind=landing
created=2026-11-16T22:04:19Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-154-conflicting-baseline-drift-recovery
epic=live-blockers
pr=#2001
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=3
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2135
steps=setup:done,implement:done,build-gate:done,self-review:clear,pr:done,reviews:done,merge:done
unresolved_review_threads=0
review_body_findings_total=6
review_body_findings_handled=6
sonar_open_new_issues=n/a
step.sonar-roundtrip.open_issue_rules=n/a
```

guard: present (opencode; `.plan/temp/guard.log`).

# PLAN-LB-154 — a conflicting baseline drift is reconciled onto the new base

Merged as PR #2001, merge commit `13e2c72e2aba3ce719ed267ed1576fadb79d95b2` (queue run 43962272549).

## Deliverables

| # | Done-when as written | Verdict | Test | Order | Failing run | Commit |
|---|---|---|---|---|---|---|
| D1 | The conflicting-drift recovery in `execution-recovery.md` gains a reconcile step between refine's return and the execute re-entry: branch brought onto the new base through the `git-workflow` verbs, ledger remapped with the PLAN-LB-91 remap | met | `test_reconcile_step_runs_between_refine_return_and_execute_reentry`, `test_every_reconcile_outcome_is_named_with_its_stop`, `test_ledger_remap_is_tied_to_a_rewriting_rebase` | `test-first` | commit `e09cce06c8d6300` (origin/main, documents unfixed): 3 failed — job log `f9534b457e994aa18248559419b6350b` | `dcc53849b`, `719fe97c6`, `5c043d744`, `53b579a2c` |
| D2 | A drift return whose probe equals the previous return's stops with a named reason on the first repeat, counter and comparison stated in `execution-recovery.md` | met | `test_unchanged_probe_stops_on_the_first_repeat` | `test-first` | same run: 1 failed — job log `f9534b457e994aa18248559419b6350b` | `dcc53849b`, `00c863d8b` |
| D3 | `refine-workflow-detail.md` § Conflict Handling and `sync-with-main.md` state the conflicting case is reconciled by the new step, not deferred to phase-6, and the non-conflicting case still self-absorbs in phase 5 | met | `test_refine_conflict_handling_names_the_reconcile_step`, `test_sync_with_main_names_the_reconcile_step` | `test-first` | same run: 2 failed — job log `f9534b457e994aa18248559419b6350b` | `93029bee8`, `719fe97c6` |

The six-failure transcript is at `.plan/temp/rb-lb-154-conflicting-baseline-drift-recovery/d1-d3-test-first-failure.md`. Two later assertions pin properties no pre-fix run could see, so they carry a `mutation-after` record instead: reverting the probe-block position and the bare `--base` form at `2af2331ec`'s tree produced exactly those two failures (job log `33b24bd56891434aa5ea602330645dc8`), and reverting the linked-worktree conflict probe produced `error` instead of `conflict` (job log `978a3535ad214ec38e014a73a3a6b45d`).

Per-head test runs (full suite): `3b52b8998` → 33 991 green (job `ca5f5de6…`); `2af2331ec` → 33 991 green (job `ca5f5de6…` family); `5c043d744` → 33 991 green (job `f1b26684…`); `3844433c9` → 34 009 green (job `5c5bb177…`); `53b579a2c` → 34 010 green (job `7928775a…`). `quality-gate` green at each of those heads.

Two deliverables share one commit: D1 and D2 both edit `execution-recovery.md`, so their prose landed in `dcc53849b`; the doc-contract test landed with D3 so every commit's tree stayed green.

## Personas and skills

- D1 and D2: `persona-implementer`; domain skill `pm-plugin-development:plugin-architecture` (declared, loaded).
- D3: `persona-documenter`; same domain skill.
- Self-review and PR-comment triage: `persona-code-reviewer` (four rounds).
- **skills added** (surface drift): none — the module was already covered. Surface additions beyond the spec's Expected Surface: `plan-marshall/workflow/execution.md` (the trigger stub, which would otherwise still describe the pre-fix loop), and `workflow-integration-git/scripts/git-workflow.py` + `standards/worktree-handling.md` + `test_git_workflow_worktree_rebase_edges.py` (the linked-worktree conflict probe the review proved dead — see Findings).

## Hypotheses

- **Refuted** — "the identical-probe comparison can use `divergent_commits` plus the conflict file set already carried in the drift TOON": the TOON carries `conflict_count`, never the file list (`phase-5-execute/standards/sync-with-main.md:74-93`, both routes). The signature uses `divergent_commits` + `conflict_count` (and `reconcile_status`/`reason` on the declined route).
- The spec's OBSERVED claims held: the old recovery (`execution-recovery.md:5-51` at base) logged, reset the phase, re-dispatched refine and re-entered execute with no ref move; the cap was 3 with the counter reset on any non-drift return; refine's Conflict Handling deferred the rebase to phase-6 branch-cleanup.

## Findings

Self-review (4 rounds, operator-approved 4th):

1. Conflict step consumed a per-file resolution refine never produces (blocker) — fixed: the step reads refine's per-path decision (`qgate list --phase 2-refine`, matched by `file_path`, case in `resolution_detail`) and authors the merge under it (`00c863d8b`, `5c043d744`).
2. No join into the remap; `pre_sha`/`post_sha` absent on the conflict route (major) — fixed: recorded around the rebase (`00c863d8b`).
3. Unchanged-probe stop ran after the phase reset (major) — fixed: moved ahead of the procedure (`00c863d8b`).
4. Minors: push failures not all dispositioned; `--base origin/…` vs the verb's contract; signature described as SHAs; sync-with-main framing; unmapped-append placeholders; missing staging/`--skip`; stale conflict list at the abort; overbroad `pre_sha` claim — all fixed (`00c863d8b`, `2af2331ec`, `5c043d744`).
5. Preferences left as-is (mis-targeted `status.metadata` assertion, illustrative token list, no branch on the `qgate list` read) — not defects; the adjacent assertions pin those contracts.

PR review (CodeRabbit, 5 + 1 findings, all fixed and replied):

1. `refine-workflow-detail.md:280` — the merge-queue `queue_wait: forbidden` override still rebases on the `true` path → `719fe97c6`.
2. `execution-recovery.md:97` — raw git commands without `-C {worktree_path}` → `719fe97c6`.
3. `execution-recovery.md:101` — a continuation completed by the caller skips the executor refresh → `719fe97c6` (`worktree-executor-refresh`).
4. `execution.md:409` trigger ignored the declined-probe route → `719fe97c6`.
5. `execution.md:409` — a stop after the rebase strands the remap/publish behind an `action: noop` retry → `719fe97c6` (`baseline_drift_reconcile` pending/done marker).
6. `execution-recovery.md:110` (major) — `worktree-rebase-to` probed `target/.git/rebase-merge`, which never matches in a linked worktree, so a real conflict surfaced as `error: rebase_failed` and the recovery's conflict route could never run → `53b579a2c`: probe resolved through `git rev-parse --absolute-git-dir`, new test staging a real `git worktree add` checkout, `worktree-handling.md` 8-state row corrected. One thread's reply text named the executor-refresh fix instead of the `-C` fix; both landed in the same commit and the sibling thread's reply says so.

## Reviewers

- **coderabbit** (required; `quota_limited`, `review_complete_after_handling`): 2026-11-16T16:20:15Z → refused (review limit). Waited 90 min per policy, re-triggered 17:51:53Z → refused; escalated `@coderabbitai full review` 17:52:48Z → refused. Waited 90 min again (17:53:05Z + 90 = 19:23:05Z), re-triggered 19:24:33Z → accepted. Reviewed `5c043d744` at 19:34:58Z (5 findings) and `3844433c9` at 20:49:03Z (1 finding); the marker names both heads. All findings fixed, every thread replied and resolved.
- **sourcery** (optional; `quota_limited`): refused at 16:20:32Z for its own 7-day budget (2 d 10 h). Optional, so not gating; not re-triggered.

## Operator questions

1. Asked: "The self-review reached its 3-round limit … the last round's two items are fixed but no review round has confirmed them. How should the run proceed?" Options: {4th confirm round, proceed and record budget-exhausted}. Selected: **"Run a 4th confirm round"**. Round 4 returned `open: none` and "the review is clear".

No free-text operator messages were used for any decision.

## Rule check

- **Guard.** `guard: present` on opencode. The guard refused one call: R1 shell-chaining on `find … | head`. The run's own record adds two read-class shell file operations the guard did not refuse — `ls -a .plan` during the setup probe and `tail -n 25` on a build log (both replaced by the Read/Grep tools). The retained `guard.log` window (1000 lines) carries no line attributable to this run's session tree; its newest entry belongs to a different session at 16:33:27Z, so "all kept" is **not** claimed.
- **Spec read.** `spec_source: ledger_worktree`; no `spec_differ` marker (the main checkout holds no copy of the spec).
- **executor-skew.** `not_applicable` — the lane text lives in a source checkout, where the executor maps that checkout's own scripts; recorded, never asked about (executor 0.1.2135).
- No spec or `.plan/orchestrator/` file was edited by this run; the one inbox message is this landing.

## Build server

- Setup preflight for the worktree: `ready` (`registered: true`).
- Mechanisms: every build routed — `daemon_longpoll`, `serialization: daemon-scheduled`. Canonicals: `module-tests` ×17 (6 full-suite, 11 focused), `quality-gate` ×9, `verify` ×2. No `in_process_fallback` and no launch-fault retry.
- Fallbacks/retries: one request — `verify` at `93029bee8` hit the explicit 1275 s bound (`timeout_used_seconds: 1275`, `timeout_source: explicit`); continued with the split form (`quality-gate` + `module-tests`), both green. No `killed` job.
- `runtime_stamp_reason`: none.

## Residue

- `PLAN-LB-153` also edits `plan-marshall/workflow/execution.md`; it landed before this PR merged and the merge resolved cleanly, but the spec's "Overlaps with: none staged" is no longer true in the ledger.
- A linked-worktree conflict now reports `status: conflict`, which also changes the behaviour of `finalize-step-sync-baseline` and `branch-cleanup` for that layout: they previously received `error: rebase_failed` where the rebase had in fact conflicted. Both handle `status: conflict`; no caller needed a change, but the fix is behavioural, not documentation-only.
- Sourcery's budget stays exhausted for ~2 days; it stays optional and non-gating.
