# Gaps — 310-baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges

**Source:** verification.md (same directory)   **Open items:** 6

## G1 — Correct the `baseline-reconcile` command-table row that still names the stored `worktree_sha` anchor

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md:184` — the `baseline-reconcile` row of the `git-workflow` command table
- **What is wrong:** The row reads "…fetches `origin/{base_branch}`, lists upstream commits **since the captured `worktree_sha`**, and runs `git merge-tree`…". D1 removed that anchor entirely: `_cmd_baseline_reconcile.py:162 _resolve_merge_base` computes `merge-base(HEAD, origin/{base})` on every call and no code reads `status.metadata.worktree_sha`. The `branch-sync-state` row six lines above (`:178`) *was* updated by the same commit, so this is a miss inside the edited region, not an untouched file.
- **Why it matters:** This table is the authoritative one-line description an agent reads when choosing the verb. It states as current behaviour exactly the defect this plan removed, and it points a reader at a field the script no longer consumes — the same class of false signal the plan exists to close. It also directly falsifies the report's "no stale 'init-time SHA anchor' prose survives".
- **Fix:** Replace "lists upstream commits since the captured `worktree_sha`" with "lists upstream commits since `merge-base(HEAD, origin/{base_branch})`, recomputed per call". While there, add "non-mutating on every classification — never moves the branch ref" to the row (it currently says only "no working-tree mutation", which understates the D2 guarantee).
- **Done when:** `grep -rn "captured \`worktree_sha\`" marketplace/` returns zero hits, and the row names the merge-base anchor.
- **Module/topic:** `plan-marshall:workflow-integration-git` — SKILL.md command table

## G2 — Correct the Step 3d skip-condition row that still says "since phase-1-init"

- **Kind:** stale-statement
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md:280` — the "Skip Conditions Summary" table row `| Zero upstream commits since phase-1-init | Fast-path log, no findings |`
- **What is wrong:** The upstream set is now `{merge-base(HEAD, origin/{base})}..origin/{base}`, not "since phase-1-init". Line 231 of this same file was correctly rewritten by the landing commit to name the merge-base and to say "never a SHA captured at plan initialisation" — line 280 contradicts it 49 lines later, in the same document.
- **Why it matters:** The two statements disagree about what a zero `upstream_commit_count` means. A reader who takes line 280 will interpret a zero as "nothing landed since the plan started" instead of "the branch is not behind", which is precisely the misreading that produced the plan's observed contradictory verdicts.
- **Fix:** Change the row to `| Zero upstream commits since merge-base(HEAD, origin/{base_branch}) | Fast-path log, no findings |`.
- **Done when:** `grep -rn "since phase-1-init" marketplace/` returns zero hits and the row agrees with line 231 of the same file.
- **Module/topic:** `plan-marshall:phase-2-refine` — `standards/refine-workflow-detail.md` Step 3d

## G3 — Document the three new return signals so a consumer is told how to handle them

- **Kind:** omission
- **Severity:** medium
- **Where:** `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_cmd_baseline_reconcile.py:439` (`head_unresolved`), `:448` (`merge_base_unresolved`), `:553` (`probe_mutated_head`); consumers `marketplace/bundles/plan-marshall/skills/phase-2-refine/standards/refine-workflow-detail.md:275-282`, `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md:78-96`, `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:228-240`
- **What is wrong:** D1 added a fail-closed skip (`merge_base_unresolved`), D3 added a skip (`head_unresolved`) and a fail-loud error (`probe_mutated_head`). `grep -rn "probe_mutated_head\|merge_base_unresolved\|head_unresolved" marketplace/` returns hits only in the script itself — no SKILL.md, no standards doc mentions any of them. The Step 3d "Skip Conditions Summary" table enumerates skip reasons and lists neither new one. The two finalize consumer docs instruct only "if the script exits non-zero → STOP and return an error TOON"; both new paths return with the wrapper's normal exit, carrying `status: skipped` or `status: error` in the payload, so that instruction does not reach them, and both docs then say "Parse the TOON return for `classification`, …" — a field neither payload contains.
- **Why it matters:** D3's whole point is that a regression is "caught at the probe, rather than discovered at the landing". A guard that emits a signal no consumer is instructed to read is caught nowhere: the finalize step will read a missing `classification` from an error payload and take an undefined branch. Same for the `merge_base_unresolved` fail-closed path.
- **Fix:** (a) Add the three reasons to the Step 3d "Skip Conditions Summary" table with their behaviour. (b) In `finalize-step-sync-baseline.md` and `branch-cleanup.md`, before the "Parse the TOON return for `classification`…" instruction, add an explicit branch: `status: error` (any `error`, `probe_mutated_head` included) → STOP and return the error TOON to the dispatcher; `status: skipped` → treat as `needs_user` and log the `reason`. (c) Add a "**Return**" block to the `baseline-reconcile` section of `workflow-integration-git/SKILL.md` listing the success fields (`classification`, `auto_reconcilable`, `merge_base_sha`, `merge_base_source`, `upstream_commit_count`, `conflicts[]`, `in_flight_files[]`), the skip reasons, and the typed error `probe_mutated_head` — the sibling `branch-sync-state` section (`:430-470`) is the shape to copy.
- **Done when:** each of the three tokens appears in at least one authoritative skill document, and both finalize consumer docs carry an explicit non-`success` branch before they parse `classification`.
- **Module/topic:** `plan-marshall:workflow-integration-git` + `phase-2-refine` / `phase-6-finalize` consumer docs

## G4 — Give the barrier re-fire mapping a test that can actually fail

- **Kind:** vacuous-test
- **Severity:** medium
- **Where:** `test/plan-marshall/workflow-integration-git/test_git_workflow.py:632-675` — `test_verdict_token_drives_refire_skip_mapping`
- **What is wrong:** The test defines its own oracle three lines above the assertion (`def verdict(state): return 'RE-FIRE' if state == 'ahead' else 'SKIP-OR-DECLINE'`) and then asserts a dict built from that function. The rule it claims to pin lives only in prose — `phase-6-finalize/SKILL.md:705-712` and `standards/push.md:119` — and `branch-sync-state` has no code consumer anywhere (`grep -rn "branch_sync_state" marketplace/**/*.py` finds only the definition and the argparse registration). Editing the SKILL.md prose back to re-firing on `remote_absent_unverified` leaves this test green.
- **Why it matters:** D4 stated "⛔ **A test is the deliverable, not a caveat in a document**" for exactly the destructive-routing half. As built, the destructive-routing half is still guarded only by a document. The regression this closes — resurrecting a merged-and-deleted branch — would return silently.
- **Fix:** Extract the mapping from prose into data the test can read. Either (a) add a small pure helper in `git-workflow.py` (e.g. `push_barrier_action(state) -> 're-fire' | 'skip'`) that `cmd_branch_sync_state` includes in its payload as `barrier_action`, have `phase-6-finalize/SKILL.md` instruct the dispatcher to branch on that field instead of on the state token, and assert the helper's output per state; or (b) if the mapping must stay in prose, have the test parse `phase-6-finalize/SKILL.md`'s item-1 block and assert that neither `remote_absent_*` token appears on a RE-FIRE line. Option (a) is preferable — it removes the prose from the decision path entirely.
- **Done when:** a test exists that fails when the push barrier is made to re-fire on `remote_absent_landed` or `remote_absent_unverified`, without the test also being the thing that defines the mapping.
- **Module/topic:** `plan-marshall:workflow-integration-git` tests + `phase-6-finalize` push barrier

## G5 — Delete the dead `auto_reconcilable == false` disjunct from the two threshold rules

- **Kind:** doc-drift
- **Severity:** low
- **Where:** `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/finalize-step-sync-baseline.md:93` and `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md:238`
- **What is wrong:** Both rules read `classification == overlap_no_content_conflict AND (auto_reconcilable == false OR {threshold} == no_overlap_only) → needs_user`. Since `_cmd_baseline_reconcile.py:492` sets `auto_reconcilable = classification == 'overlap_no_content_conflict'`, the first disjunct can never be true inside a branch already conditioned on that classification — both docs even say so in a trailing parenthetical ("always reports `auto_reconcilable == true`"). Relatedly, `auto_reconcilable` is now `false` on `no_overlap`, a state that is trivially reconcilable, so the field carries no information the `classification` token does not already carry.
- **Why it matters:** A decision rule with an unreachable branch, annotated as unreachable, invites a reader to believe the classifier can downgrade auto-resolution — it no longer can. It is dead surface in a decision table an agent executes.
- **Fix:** Reduce both rules to `classification == overlap_no_content_conflict AND {threshold} == no_overlap_only → needs_user`, keeping the explanatory sentence. Decide separately whether `auto_reconcilable` should be dropped from the payload as redundant with `classification`; if it is kept, say in `workflow-integration-git/SKILL.md` that it is derived from `classification` and is not an independent signal.
- **Done when:** neither doc contains `auto_reconcilable == false` as a live condition.
- **Module/topic:** `plan-marshall:phase-6-finalize` — sync-baseline / branch-cleanup threshold rules

## G6 — Correct the two factual errors in this plan's own run report

- **Kind:** stale-statement
- **Severity:** low
- **Where:** `doc/plans/truthful-signals/310-baseline-reconcile-anchors-on-a-stale-phase-1-sha-and-one-verdict-auto-merges/report-01.md:3` (header) and the § Build gate paragraph
- **What is wrong:** (a) The header still reads "**PR:** _pending_    **Outcome:** _in progress_" although the change landed as PR #1206 / `60e5fd81`, and the report's own § Contract check names PR #1206 — the document contradicts itself. (b) § Build gate says "three `.py` files" and then enumerates four (`_cmd_baseline_reconcile.py`, `git-workflow.py`, and two test modules); `git show --name-only 60e5fd81` confirms four. (c) § Findings claims "no stale … 'init-time SHA anchor' prose survives", refuted by G1 and G2.
- **Why it matters:** The report is the durable record of this run and is the input to retrospective audits. A count that is off by one and an "outcome: in progress" on a landed plan both mislead a later reader, and the clean-sweep claim is the one an auditor would otherwise trust instead of re-deriving.
- **Fix:** Set the header to `**PR:** #1206  **Outcome:** merged as 60e5fd81`; change "three `.py` files" to "four `.py` files"; and either strike the "no stale init-time SHA anchor prose survives" clause or scope it to the files it actually checked, noting the two sites listed in G1/G2.
- **Done when:** the report's header, its `.py` count, and its sweep claim all agree with the landed diff and the tree.
- **Module/topic:** `doc/plans/truthful-signals/310-…` — run report
