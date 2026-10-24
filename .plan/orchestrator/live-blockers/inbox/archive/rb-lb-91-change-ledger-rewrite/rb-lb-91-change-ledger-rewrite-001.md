envelope_version=1
sender_type=plan
sender_id=rb-lb-91-change-ledger-rewrite
epic=live-blockers
kind=landing
created=2026-10-23T20:52:43Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-91-change-ledger-rewrite
epic=live-blockers
pr=#1847
merge_state=merged
cleanup_owed=false
deliverables_total=2
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.1996
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=0
step.sonar-roundtrip.open_issue_rules=none
```

guard: present (this harness has the tool-call guard installed)

# PLAN-LB-91 landing — remap rewritten commits / name the rewrite at the 5-execute boundary

Merged as `5a6058a6e46b32657b466e04ee3a57e867c47fad` (PR #1847).

## Deliverables

### D1 — a rewrite is mapped onto the ledger without breaking append-only (met)

- **A fixture branch with three recorded commits is rebased; after the remap the 5-execute boundary no longer reports them unrecorded, and the ledger still holds the original rows.** met. Test `test_rebase_remap_clears_the_boundary_and_keeps_original_rows`. order: `test-first`. Failing run: `5fdec1ceb`, build log `python-2026-10-23-091733.log` (`invalid choice: 'remap'`). Passing run: `bf5cee688`, `python-2026-10-23-165010.log` (31994 tests). Commit `089bc2a1c` (plus `a3b48690d`, `bf5cee688`).
- **A fixture amend maps the same way.** met. Test `test_message_only_amend_maps_the_same_way`. order: `test-first`. Failing run: `5fdec1ceb`, `python-2026-10-23-091733.log`. Passing run: `bf5cee688`, same log. Commit `089bc2a1c`.
- **At HEAD the boundary refuses with all three unrecorded (HYPOTHESIS).** met. Test `test_boundary_refuses_all_three_commits_after_rebase_before_remap`. order: `none` — the clause asserts pre-existing behaviour and is green at the base (`5fdec1ceb`, `python-2026-10-23-091733.log`: 1 passed, 5 failed), so no failing output is claimed for this clause. Commit `bf5cee688` (assertion strengthened).
- **The rewriting step emits the map and the remap consumes it.** met. Test `test_emit_map_dry_run_writes_the_map_without_appending_then_the_map_is_consumed`. order: `test-first`. Failing run: `5fdec1ceb`, `python-2026-10-23-091733.log`. Passing run `bf5cee688`. Documented in `finalize-step-sync-baseline.md` (emit with `--old-head {pre_sha} --emit-map … --dry-run`, consume with `--map-file`), commit `089bc2a1c` + `bf5cee688`.

### D2 — the refusal names the rewrite and carries the repair (met)

- **A fixture whose every row was rewritten returns the rewrite signature with the remap invocation.** met. Tests `test_whole_branch_unrecorded_reports_rewrite_signature_with_remap` (unit) and `test_boundary_refuses_all_three_commits_after_rebase_before_remap` (real rebase). order: `test-first`. Failing run: `5fdec1ceb`, `python-2026-10-23-091910.log` (`AttributeError: _sha_is_ancestor_of_head`). Passing run `bf5cee688`, `python-2026-10-23-165010.log`. Commits `12f9a0a48`, `640e545f0`.
- **A fixture with one missing row returns the plain gap with its append invocation.** met. Test `test_one_missing_row_reports_plain_gap_with_append_invocation`. order: `test-first`. Failing run: `5fdec1ceb`, `python-2026-10-23-091910.log`. Passing run `bf5cee688`. Commit `12f9a0a48`.

Per-head test runs (`module-tests`) against pushed heads: `089bc2a1c` (parallel run hit a pre-existing target-tree generation race; isolated serial re-run green, `python-2026-10-23-093610.log`), `12f9a0a48` green 26858 (`python-2026-10-23-093720.log`), `d17106e6a` green 26927 (`python-2026-10-23-152726.log`), `a3b48690d` green 26929 (`python-2026-10-23-155357.log`), `bf5cee688` green 26930 (`python-2026-10-23-165740.log`). `pw verify` green at `4e82c074e` (31930), `d17106e6a` (31991), `101253ed8` (31993), `a3b48690d` (31993), `bf5cee688` (31994, `python-2026-10-23-165010.log`).

## Personas and skills

- production code (D1, D2): `persona-implementer` + `ref-code-quality`.
- tests: `persona-module-tester`.
- self-review rounds and every PR-comment triage: `persona-code-reviewer`.
- docs (SKILL.md, sync-baseline standard): `persona-documenter` judgement applied.
- Deliverable declarations: `skills: none named` / no `Persona:` line in the spec, so the persona table selected the above.

## Hypotheses

- **After a rebase every recorded SHA is absent from `git rev-list {merge_base}..HEAD`, so the refusal covers the whole branch.** Confirmed — `test_boundary_refuses_all_three_commits_after_rebase_before_remap` (real rebase) and `test_rebase_remap_clears_the_boundary_and_keeps_original_rows`; the predicate is `_sha_is_recorded` in `_cmd_lifecycle.py` (prefix-only comparison) and `_branch_commit_shas` (`git rev-list merge_base..HEAD`).
- **A patch-id match recovers every rebased commit except one whose patch changed; such a commit needs the explicit append path.** Confirmed — `test_content_changing_amend_is_reported_unmapped` reports it via `unmapped`, and `_derive_patch_id_map` (stable `git patch-id`) matches the rest.
- **Verify-first clause (where the remap is invoked, and whether the prefix rule absorbs part of the case).** Chosen: the rewriting step (`sync-baseline`) invokes it, because that step knows a rewrite happened and holds `pre_sha`; the boundary only emits a ready-to-run invocation for out-of-band rewrites (a boundary-side auto-remap would mutate the ledger on a read path). The prefix rule in `_sha_is_recorded` does not absorb the case: a rewritten SHA shares no prefix with its predecessor. Recorded in `_rewrite_evidence`'s docstring (`_cmd_lifecycle.py`) and the sync-baseline standard.

## Findings

- **Self-review round 1** (9 findings): fixed the whole-branch staleness claim (both remedies), the second-criterion test reachability, missing emit-map/dry-run/old-head/map tests, writer-count wording, the append placeholder, the undocumented `rewrite_detected`, fail-closed map parsing + unmatched-key reporting, `remap_count` documentation; declined the relative-executor-path note (the sanctioned form, same cwd). Commit `6c22918fd`.
- **Self-review round 2**: tri-state ancestry (`commit_ancestry`), append remedy now carries `changed_paths` + replace-placeholders text, partial explicit-map reporting, sync-baseline wiring, boundary-reports wording. Commit `b2d520957`.
- **Self-review round 3**: whole-branch state always ambiguous (both remedies + observed-state message), tri-state remap ancestry, unresolvable `--old-head` refused, `--old-head` documented for what it narrows, real-rebase test pins the signature. Commit `b971a97ad`. Open at the round limit: the remap test module keeps its own repo/ledger fixture instead of the shared preamble (Low; operator accepted the residue). State: `budget-exhausted`.
- **CodeRabbit pass 1 (head `4e82c074e`, 5 findings)**: `--old-head` scoping (scoped half fixed, mandatory-scope declined because D2's remedy must run), idempotency SHA form, mixed-gap remap remedy, remap failure branch in the sync-baseline doc, unfalsifiable negative assertion. All fixed (`6abaaca4d`, `640e545f0`), replied and resolved.
- **CodeRabbit pass 2 (head `d17106e6a`, 3 findings)**: superseded originals re-reported on a second rewrite, per-source pair tracking, append scope in the sync-baseline doc. All fixed (`a3b48690d`, `101253ed8`), replied and resolved.
- **CodeRabbit pass 3 (head `101253ed8`, 2 inline + 1 outside-diff)**: row identity across differing facts, `changed_paths` sourced from the rebased commit, replacement SHA for `unmapped` commits. All fixed (`bf5cee688`), threads replied and resolved; the outside-diff finding answered on the PR (`issuecomment-6370590794`).
- **CI failures**: two PR `verify` runs failed on the project's mypy cache-freshness heuristic (`test-compile` 204/211 files/s vs a 200 ceiling) — not code failures; reruns passed. The merge-group run 40006923957 failed on the same heuristic, was rerun successfully (operator-selected), and the fresh merge-group run 40018967331 passed.
- **Orchestrator notice**: PLAN-LB-43 touches `_cmd_lifecycle.py` in the same region group; the change stayed confined to the D2 refusal region and absorbed none of LB-43's intent.

## Reviewers

- **coderabbit** (required, quota_limited): reviewed as a formal review at `4e82c074e` (14:15:51Z), `d17106e6a` (15:32:44Z) and `101253ed8` (16:38:18Z), covering 10 findings, all handled. The current head `bf5cee688` was re-triggered after the last push (17:59Z) and refused on quota (17:59:12Z); an earlier trigger-7 at 17:06Z also refused. Standing review authorization applied: qualifying review exists (`ci pr reviews` lists the `101253ed8` review with its commit id), every finding fixed or answered, every thread resolved, re-trigger refusal recorded, and every other gate condition held on `bf5cee688` (PR CI green, `pw verify` green locally and on the PR verify job after rerun, Sonar 0, base not moved).
- **sourcery** (optional, quota_limited): refused on hard quota at 11:01:33Z (4 days 2 hours); not gating.

## Operator questions

1. Asked: continue with a 4th self-review round or accept the residue (one Low finding). Options: {Accept residue, proceed to PR; Run a 4th review round}. Selected: **Accept residue, proceed to PR**.
2. Asked: lane-text/executor skew (the base merge brought a lane text requiring `executor-skew`/`build-routing`; the executor and installed flat lane lacked them). Options: {Continue under the loaded text; Regenerate executor first; Stop as blocked}. Selected: **Regenerate executor first**. The executor was regenerated; `executor-skew` then answered `could_not_check` (the flat install carries no version metadata) and `build-routing` answered `auto`.
3. Asked: the merge queue dequeued on the mypy cache-freshness heuristic. Options: {Re-enqueue now; Stop with the PR open; Rerun the merge-group run first}. Selected: **Rerun the merge-group run first**. The rerun passed and the PR was re-enqueued.
4. Free-text: an orchestrator notice that PLAN-LB-43 collides on `_cmd_lifecycle.py`; no action was requested and the change was kept confined.

## Rule check

- Guard: **present**. `guard_log` `.plan/temp/guard.log` carries two refusals for this run's session (`ses_e97f7fe8affeJaft3TAYDXIQ0u`): R5 at 16:29:18Z and R5 at 17:16:54Z, both from typing `plan-marshall:tools-integration-ci:ci` after `python3 .plan/execute-tool` instead of `.plan/execute-script.py`; both were retried correctly in the same step.
- The run's own shell file operations, counted beyond the guard: read-class `ls` (worktree `.plan`, `target/`, the worktree executor), `tail` on build logs, `grep -n` on `pyproject.toml`, `readlink`, `date`; these are file reads the shell rule routes through the file tools, and they are reported here as kept-with-exception. No shell write/redirect was issued.
- One write outside the lane boundary, operator-authorized: `generate_executor.py generate` wrote `.plan/execute-script.py` in the main checkout (selected "Regenerate executor first").
- The merge commit message says `merge origin/main into feature/…` rather than the merged text's `merge: origin/main into …` template; it carries the resolved commit trailer.

## Build server

- Setup preflight: `ready`. The first routed build failed because the worktree had no `.plan/execute-script.py` at that moment (`executor_absent_from_worktree`); every build then ran with `--execution-mode in_process` (mechanism `in_process_fallback`). The worktree executor appeared at 11:18Z, and `build-routing` later answered `auto`.
- No daemon-routed build was used, so no routed job could interleave; no `killed` job.
- `runtime_stamp_reason`: absent. `executor_version` read at setup was `0.1.1989`; after the operator-authorized regeneration it is `0.1.1996`.

## Residue

- The remap test module keeps its own git-repo/ledger fixture instead of reusing `_manage_change_ledger_fixtures` (Low; accepted at the self-review round limit).
- D2's "ready-to-run append invocation" carries documented `DELIVERABLE_ID` / `CHANGED_PATHS` placeholders because the boundary cannot know them; every message says to replace both.
- `executor-skew` reports `could_not_check` on this flat install (no version metadata); `resolve` still reports the executor version, so the stamp is read from there.
- PLAN-LB-43's uncommitted `_cmd_lifecycle.py` change may conflict with this PR's D2 region; the intended resolution is to keep this PR's refusal logic and re-apply LB-43's own change on top.
