# Verification — 310-baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges

**Verified against:** commit `2402b02bf5bc64b5ece468b6d2a3e884b5f0b30d`   **Landed as:** PR #1206, commit `60e5fd81b48949d455413a84975cc39e79475f94`   **Verdict:** implemented-with-gaps

## Method

Read `plan.md` and `report-01.md` in full. Located the landing with `git log --oneline --all --grep '#1206'`, read `git show --stat 60e5fd81` and the per-file diffs for both scripts and all six docs. Read the pre-fix file (`git show 60e5fd81^:…/_cmd_baseline_reconcile.py`) to confirm the plan's asserted-absence hypotheses at source.

Files opened at HEAD:

- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_baseline_reconcile.py` (all 613 lines)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` (`cmd_branch_sync_state` and helpers, lines 1152–1285; argparse registration line 2128)
- `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md` (command table, `### branch-sync-state`, `### baseline-reconcile`)
- `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md` (Step 3d, lines 205–285) and `phase-2-refine/SKILL.md:129`
- `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md`, `standards/branch-cleanup.md`, `standards/push.md`, `SKILL.md` (push-barrier re-entry block)
- `test/plan-marshall/workflow-integration-git/test_baseline_reconcile.py`, `test_git_workflow.py`
- `marketplace/bundles/plan-marshall/skills/plan-marshall/scripts/_invariants.py` (`_capture_worktree_sha`, line 704) to check the sibling-field coupling claim

Commands run:

- `uv run python -m pytest test/plan-marshall/workflow-integration-git/test_baseline_reconcile.py -o addopts="" -q` → **25 passed**
- `uv run python -m pytest test/plan-marshall/workflow-integration-git/test_git_workflow.py -o addopts="" -q` → **96 passed** (25 + 96 = 121, matching the report's "121 scoped tests")
- Tree-wide sweeps for `no_remote`, `auto_reconciled`, `merge_failure_paths`, `baseline_drift_reconcile_failed`, `auto_reconcilable`, `merge_commit_sha`, `worktree_sha`, `since phase-1-init`, `since the captured`.

Mutations applied (file byte-snapshot taken to the scratchpad first; `git diff --quiet` confirmed the file was not concurrently modified; restored from the snapshot, and `git diff --quiet` confirmed clean afterwards — no `git checkout`/`restore`/`stash` used):

1. **Anchor mutation** — re-introduced the defect by making `_resolve_merge_base` prefer `status.metadata.worktree_sha` when present. Result: **3 failed / 22 passed** — `test_two_calls_after_reconcile_agree_zero_upstream_no_overlap`, `test_in_flight_set_excludes_files_the_plan_never_touched`, `test_merge_base_recomputed_not_read_from_stored_status` all went RED. The D1/D5(a)/(b)/(c)/(d) tests are non-vacuous.
2. **D3 guard mutation** — replaced the post-probe condition at line 552 with `if False:`. Result: **1 failed / 24 passed** — `test_d3_guard_fires_when_probe_moves_head` went RED. The D3 guard is the only thing that test passes on.

## Deliverable-by-deliverable

| # | Deliverable | Done-when condition | Implemented? | As documented? | Correct? | Complete? | Evidence (file:line / symbol / command + result) |
|---|---|---|---|---|---|---|---|
| D0 | GATE: enumerate anchor readers + verdict side effects | Both directions enumerated, population stated | yes | yes | yes | yes | `report-01.md` § D0. Re-derived: `_resolve_baseline_sha` (pre-fix `_cmd_baseline_reconcile.py:159`) was the only reader of `status.metadata.worktree_sha` as a git SHA; grep over `marketplace/**/*.py` finds no other reader today (`_invariants.py:704 _capture_worktree_sha` computes it live via `git_head`, does not read the field; `manage-change-ledger` / `manage-architecture` hits are `compute_worktree_sha`, a content hash). Only ref-moving side effect pre-fix: `git merge origin/{base} --no-edit` at `60e5fd81^:…:415`. Blast radius correctly reported not knowable (`.plan/` git-ignored). |
| D1 | Anchor on merge-base of HEAD and base, per call | No range computed from a stored SHA | yes | yes | yes | **no** | `_cmd_baseline_reconcile.py:162 _resolve_merge_base`, called at `:443` inside `cmd_baseline_reconcile` (no cache, no module-level memo). Both ranges anchor on it: `:294 _list_upstream_commits` (`{mb}..origin/{base}`) and `:598 _list_in_flight_files` (`{mb}..HEAD`). Fails closed at `:445` with `merge_base_unresolved`. Mutation 1 confirms the tests bind. **Incomplete:** two docs still state the old anchor — see G1, G2. |
| D2 | Probe non-mutating on every path | No classification path moves a ref | yes | yes | yes | yes | The whole focused-reconcile block is gone; classification at `:475-481` derives from `merge-tree --write-tree` (`:341 _detect_merge_conflicts`) plus the file-set intersection. `auto_reconciled`/`merge_failure_paths`/`baseline_drift_reconcile_failed` are zero-occurrence tree-wide. Dependency check: no flow depended on the merge — `finalize-step-sync-baseline.md:30` and `branch-cleanup.md` § "Rebase Branch onto Base" perform the rebase via `worktree-rebase-to`; made explicit in all four consumer docs. |
| D3 | Fail-loud guard: post-probe HEAD assertion | Regression caught at the probe | yes | yes | yes | **no** | `head_before` at `:434`, `head_after` + guard at `:549-560` returning `status: error, error: probe_mutated_head` ahead of the payload and ahead of the persist-failure arm. Mutation 2 confirms the guard is what makes `test_d3_guard_fires_when_probe_moves_head` pass. **Incomplete:** `probe_mutated_head` (and the two new skip reasons) appear in no skill document — see G3. |
| D4 | Verdicts reconcilable; ambiguous verdict must not route to a destructive action | A test pins both | yes | yes | yes | **partly** | Half 1: `test_two_calls_after_reconcile_agree_zero_upstream_no_overlap` (real git fixture, real merge, asserts equal classification + 0 upstream). Half 2: `git-workflow.py:1195 cmd_branch_sync_state` splits the absent-ref case into `remote_absent_landed` (`:1268`, proven by `:1179 _head_contained_in_base`) and `remote_absent_unverified` (`:1277`, the decline). `no_remote` as a *state* is gone tree-wide. **But** the "must not route to a destructive action" half is pinned by `test_verdict_token_drives_refire_skip_mapping`, whose mapping is a lambda defined inside the test — see G4. |
| D5 | Five tests (a–e), each red pre-fix | All five pass, each seen red first | yes | yes | yes | yes | (a)+(d) `test_baseline_reconcile.py:941`; (b) `:992`; (c) `:1027`; (e) `:1060`; plus D3 `:1111`. All 25 pass at HEAD. Red-first independently re-derived for (a),(b),(c) by mutation 1 and for D3 by mutation 2; (e) is a regression guard that is trivially green post-fix by construction (the merge call no longer exists). |

**D1 — incomplete sweep.** The code is right; two prose sites still state the removed anchor. `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md:184` (the `baseline-reconcile` row of the command table) reads "lists upstream commits since the captured `worktree_sha`". The very same table's `branch-sync-state` row six lines above was edited by this commit, so the miss is inside the edited region. `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md:280` reads "Zero upstream commits since phase-1-init" in the Step 3d "Skip Conditions Summary" — again in a file this commit edited (line 231 of the same file was correctly updated to name the merge-base).

**D3 — undocumented signal.** `probe_mutated_head`, `merge_base_unresolved` and `head_unresolved` exist only in the script and its tests. `workflow-integration-git/SKILL.md`'s `baseline-reconcile` entry documents no return fields or reasons at all; `refine-workflow-detail.md:275-282`'s "Skip Conditions Summary" enumerates the skip reasons and omits both new ones; the two finalize consumer docs only instruct "if the script exits non-zero → STOP", which does not cover a `status: skipped` or a `status: error` returned with exit 0. A guard whose signal no consumer is told to read is only half a fail-loud.

**D4 — the routing half is untestable as built.** `branch-sync-state` has no code consumer at all (grep over `marketplace/**/*.py` finds only the script's own definition and the tests); the push barrier's re-fire rule lives in `phase-6-finalize/SKILL.md:705-712` prose. The test's mapping half therefore asserts a dictionary derived from a lambda declared three lines above it, and would stay green if the SKILL.md prose were edited back to re-firing on a ref-absent state.

## Report accuracy

Contradictions found:

1. **"no stale … 'init-time SHA anchor' prose survives"** (§ Findings, verification-sub-agent paragraph) — **contradicted**. `workflow-integration-git/SKILL.md:184` and `phase-2-refine/standards/refine-workflow-detail.md:280` both still state the init-time anchor. The sub-agent's sweep, and the report's endorsement of it, are wrong on this point.
2. **"three `.py` files: `_cmd_baseline_reconcile.py`, `git-workflow.py`, and two test modules"** (§ Build gate) — the enumeration names **four** files. Re-derived from `git show --name-only 60e5fd81`: `_cmd_baseline_reconcile.py`, `git-workflow.py`, `test_baseline_reconcile.py`, `test_git_workflow.py`. The count word is wrong; the verdict it supports (build gate takes the full path) is unaffected.
3. **Header fields** — "**PR:** _pending_    **Outcome:** _in progress_" while the same document's § Contract check names PR #1206 and the change landed as `60e5fd81`. Internally inconsistent and now stale.

Checked and found accurate: the D0 enumeration (single git-SHA reader; the other `worktree_sha` matches are a different content-hash concept); "`auto_reconciled`/`merge_failure_paths`/`baseline_drift_reconcile_failed` are zero-occurrence in the bundle" (re-derived: 0 hits each); "no `no_remote` state token survives … except the … probe skip-reason" (re-derived: exactly one hit, `_cmd_baseline_reconcile.py:405`, the no-git-remote skip — line number has shifted from the reported 386 because of a later unrelated commit); "the surviving `merge_commit_sha` hits are the legitimate `references.merge_commit_sha` landing field" (re-derived: all 10 hits are `manage-references` / `plan-retrospective` / `branch-cleanup` landing-field uses); "all 121 scoped tests pass" (re-derived: 25 + 96 = 121, all pass); "the finalize steps already performed their own rebase and never depended on the probe's merge" (confirmed at `finalize-step-sync-baseline.md:30` and `branch-cleanup.md` § Rebase Branch onto Base); the D3-fires claim (re-derived by mutation); PR #1206 and the CLI `--help` fix in `51e4c55` (present at `git-workflow.py:2131-2132`).

## Out-of-scope compliance

Compliant. The landed diff touches 11 non-plan files, all inside the declared Expected surface: the two scripts, their two test modules, and seven consumer docs in `workflow-integration-git`, `phase-2-refine`, `phase-6-finalize`. No collateral change outside those bundles.

- "Changing what the anchor field means for its other consumers" — honoured; `manage-status` is untouched, and D1 removes the read rather than redefining the field (the plan listed `manage-status/**` as expected surface, and the run correctly landed nothing there, explaining why).
- "Hardening the auto-merge rather than removing it" — honoured; the merge block is deleted, not guarded.
- "A general branch-recovery workflow" — honoured; `remote_absent_unverified` declines and no recovery path was designed.

## Residue carried forward

- **"The arm-once-green step is the only remaining action."** — **closed.** PR #1206 landed as `60e5fd81` on `main`; a later plan (#1210) sanctioned the arm-and-hand-off contract change the report proposed under "What have we learned".
- **"No code, test, or doc residue — all deliverables landed in commits on this branch."** — **contradicted by today's tree**: two stale doc statements survive (G1, G2), plus the undocumented new signals (G3).

## What could NOT be verified

- The whole-tree figures `19463 passed, 14 skipped, 0 failed` and the `./pw quality-gate` clean result — the tree has advanced ~18 commits since the landing, so those numbers are not re-derivable at HEAD, and a whole-tree run was out of proportion for this check.
- The red-first claim for the remaining 7 of the reported 11 pre-fix failures (the `auto_reconcilable` rename updates, the `overlap_no_content_conflict` non-mutating rewrite, and the three branch-sync-state D4 tests). Four were re-derived by mutation; the rest were taken as read.
- The historical blast radius of the auto-merge — genuinely not knowable from this clone, exactly as the report states (`.plan/` is git-ignored and absent).
- CI check-run states on head `51e4c55` and the reviewer-participation table — provider-side facts, not derivable from the tree.
- Whether `status.metadata.worktree_sha` still has any live reader anywhere outside `marketplace/` (the sweep covered the bundle tree and `test/`).
