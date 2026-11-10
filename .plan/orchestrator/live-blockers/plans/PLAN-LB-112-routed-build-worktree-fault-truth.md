# PLAN-LB-112: A routed build's resolution fault reaches the caller as itself, and `--plan-id` resolves to the tree the routing process already found

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-112-routed-build-worktree-fault-truth.md` and is queued as one row file, `queue/PLAN-LB-112.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged in the 2026-11-04 inbox drain from the finding `lessons-routing-076`, graded **high** by the operator. Its source is
> API-Sheriff lesson `2026-08-09-03-002`, which the finding says was read from code and **not reproduced by an executed run**. The
> code facts were re-read at HEAD for this draft and hold (see Claim Labels). The runtime failure is a hypothesis, and D1 settles
> it before anything is changed.

## Objective

A daemon-routed build run with `--plan-id`, in the window after the plan's worktree contents were moved back into the main
checkout and before the worktree directory is removed, is reported as a red build. The inner process fails to resolve the plan's
worktree and exits with `worktree_resolution_failed`. The outer wrapper does not surface that error: it folds the failure into
`build_failed` and a synthetic "no structured errors were parsed" row. A routing fault is reported as a build failure, and the
factory's statement that `--plan-id` "resolves identically in both processes" is false for that window.

After this plan, three things hold. First, whether the failure happens is established by a run, not by reading. Second, if it
happens, the daemon child is given the tree the routing process already resolved and does not resolve it again. Third, any
structured fault the child emits before the build tool runs reaches the caller under its own name with its own reason.

## Deliverables

1. **The failure is reproduced, or the premise is refuted, before any code changes.**
   - Reproduce the window: a plan whose worktree contents were moved back and whose worktree directory still exists, a build routed
     to the daemon with `--plan-id`, and the same build run in process. Record both results in the PR.
   - If the routed run reports `worktree_resolution_failed` as itself, the hypothesis is refuted at code: record the cause that
     differs, close D2 to D4 as not needed, and keep only the corrected docstring (D4) if it is still false.
   - If the routed run reports `build_failed` with the synthetic row, D2 to D4 proceed.
   - The reproduction states which copy of the script ran. A call through this repository's executor runs the source tree, and a
     reproduction that does not say so can be about a different tree.

   *Done when:* the PR records the routed and in-process results of one reproduction with the copy that ran, and states
   `reproduced` or `refuted`. A fixture test that drives the routed path with a moved-back plan (a plan directory absent in the
   child's tree, a worktree path persisted in the parent's status) is red at HEAD when the verdict is `reproduced`.

2. **The daemon child resolves the same tree as the routing process.**
   - The routing process has already resolved the tree it submits (`exec_root`, `_route_to_daemon`). The child is re-run with the
     original argv, which carries `--plan-id` through unchanged, and re-resolves it from its own working directory, where the plan
     directory is absent after move-back.
   - The outline chooses how the child is given the resolved tree. The candidates are: carry the resolved tree to the child in the
     re-run command, or make the child's resolution consult the same sibling-worktree lookup the locator already uses. The
     constraint is attribution: the plan id must still reach the child's ledger row and slot accounting, so replacing `--plan-id`
     with `--project-dir` alone is not enough, and the two flags stay mutually exclusive.
   - The strict gate of `get-worktree-path` stays strict. Its docstring records why: `locate-plan-checkout` calls back into it, so a
     fallback there would make the consult call itself.
   - The routed re-run keeps `_absolutise_project_dir` and every token it does not touch, as PLAN-LB-104 shipped them.

   *Done when:* the D1 fixture is green for a routed build with `--plan-id` after move-back, and the result is the build's own
   result, with the plan id on the ledger row. A direct, non-routed build behaves as before. The `--project-dir` routed cases from
   PLAN-LB-104 stay green unchanged.

3. **A structured fault the child emits before the tool runs reaches the caller as itself.**
   - Today the routed result is built from the daemon's job outcome. A child that exits 2 with a TOON error body
     (`worktree_resolution_failed`, `mutually_exclusive_args`) is treated as a failed build, and the synthetic row is emitted
     because no structured issue was parsed. `LAUNCH_FAULT_ERRORS` holds only `execution_failed` and `log_file_failed`, so these
     faults cannot travel as themselves.
   - A fault the child reports through its own error emitter, before any build tool ran, is carried to the caller with its `error`
     name, its reason and its exit code. The outline decides whether that is a new member of the launch-fault set, a pass-through of
     the child's own structured error, or both. A build that ran and failed keeps `build_failed` and keeps the synthetic row.
   - The result formatter's field whitelist carries any new field on both the TOON and the JSON path.
   - A direct, non-routed build already reports `worktree_resolution_failed` as itself with exit 2; the routed path matches it.

   *Done when:* a routed fixture whose child prints the `worktree_resolution_failed` error body and exits 2 returns that error name
   and reason with exit 2 and no synthetic row. A fixture whose child ran the tool and failed still returns `build_failed` with the
   row. Both are red at HEAD for the first case.

4. **The factory docstring states the invariant that holds.**
   - The statement that `--plan-id` "resolves identically in both processes" is rewritten to state when that is true and what
     guarantees it after D2, or is removed if D1 refutes the premise and the statement holds.
   - Every other comment that repeats the claim is corrected the same way.

   *Done when:* no comment or doc states the identical-resolution invariant in a form D1 or D2 contradicts, and a search for the old
   sentence returns no hit that is false.

Split guard: four deliverables, one fault path. D1 decides whether the rest is needed, and D2 and D3 are independent halves of the
fix (the cause, and the reporting). D4 is a comment pass.

## Standing Constraints

- **Reproduce before changing.** D1 is first and can end the plan. If HEAD already reports the fault as itself, loop back and
  re-scope rather than change the routing.
- **A routing fault is never a red build.** Anything that stops the tool from running is reported as itself. `build_failed` means the
  tool ran and failed.
- **Leave routing alone.** Do not change the semantics of `--execution-mode`, `build-routing`, or the `--project-dir`
  absolutisation from PLAN-LB-104.
- **The strict `get-worktree-path` gate is kept.** Do not add a fallback to that verb.
- **Fail closed.** A tree that cannot be resolved is an error, not a default to the main checkout.
- **Tests state their purpose.** Every new or changed test states what it protects, uses the `PLAN_MARSHALL_HOME` fixture, never
  reads the real `~/.plan-marshall` or this repository's live `.plan/marshal.json`, and is shown red at HEAD where its Done-when says so.
- **The daemon side takes effect only after a reconcile.** The child runs the executor under the daemon; a live record from a worktree
  before the merge is NOT a Done-when (PLAN-LB-104's D1 live clause failed for exactly this reason). The PR's evidence is the fixture
  suite plus D1's record, and the landing lists any post-merge live check as owed.
- **No Sonar.** Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: `_route_to_daemon` re-runs the executor under the daemon with `sys.argv[1:]`, rewriting only `--project-dir` through
  `_absolutise_project_dir`, so `--plan-id` passes through unchanged — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` L1032-1044, at HEAD. The finding
  cites L1036-1047; the lines moved by a few.
- OBSERVED: the docstring claiming `--plan-id` "resolves identically in both processes" is at the same file, L929-937 (the finding
  cites about L932-935), in the `_PROJECT_DIR_FLAG` block docstring.
- OBSERVED: `get-worktree-path` keeps the STRICT gate on purpose, with no sibling-worktree fallback, because
  `git-workflow locate-plan-checkout` calls back into it — read at
  `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py` L676-681.
- OBSERVED: `LAUNCH_FAULT_ERRORS = frozenset({ERROR_EXECUTION_FAILED, ERROR_LOG_FILE_FAILED})` — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` L267. The docstring says a consumer must
  report one of these as itself.
- OBSERVED: when a build fails and the log parser extracted no structured error, exactly one synthetic row is emitted
  ("Build failed but no structured errors were parsed; see full log") — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` L1033-1049.
- OBSERVED: a direct, non-routed build reports `WorktreeResolutionError` through `emit_worktree_error` and exits 2 — read at
  `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_cli.py` L679-690. So the misattribution is specific to
  the routed path, as the finding says.
- HYPOTHESIS: the inner process fails after move-back. It runs with its cwd set to the worktree, where the plan directory is absent,
  and the strict gate then fails. This is the finding's reading of code, "not reproduced by an executed run", and it is also not
  reproduced here. D1 settles it.
- HYPOTHESIS: the daemon child's structured error body is discarded or not parsed on the routed result path, so only `build_failed`
  and the synthetic row come back. Locate the routed result construction and the daemon job outcome handling at outline
  (`_build_execute_factory.py` § the code after the wait, and `marshalld.py` § `_execute`; verify-at-outline).
- HYPOTHESIS: the field whitelist the result formatter needs is `_build_format.EXTRA_FIELDS`, where PLAN-LB-104's landing found it
  (verify-at-outline).
- Verify-first clause (D1): run the reproduction at HEAD first. The finding's own narrowing facts bound the window — only between
  move-back and worktree removal, only a daemon-routed build, an immediate failure, and `--project-dir` as a workaround — and
  those are why the grade was borderline. Record whether the window is reachable in a normal plan run (the lane's own move-back and
  removal order), because that decides how much D2 matters.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — the routed re-run, the routed result path, the docstring (D2, D3, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` — launch-fault set (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — the synthetic-row path, only if D3 changes it (D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_format.py` — field whitelist (D3; verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_query.py` — only if D2 chooses the sibling-lookup candidate; the strict gate is not changed (D2; verify-at-outline)
- OBSERVED: `test/plan-marshall/build-server/test_build_execute_routing.py` — routed fixtures (D1, D2, D3)
- OBSERVED: `test/plan-marshall/script-shared/test_build_execute_factory.py` — factory and docstring guards (D2, D4)

## Dependencies and Sequencing

- **Depends on:** none. PLAN-LB-104 (PR 1893) is shipped and present in HEAD; this plan builds on its `_absolutise_project_dir` and its
  launch-fault reporting.
- **Overlaps with PLAN-LB-108 (staged).** Both edit `_build_execute_factory.py` (LB-108 in `_route_to_daemon` for the `queued` wait
  status and the in-process lock) and both declare `test_build_execute_routing.py`. Two shared files reach the gate's overlap prompt.
  **Run them in sequence, never concurrently; this plan is the smaller and can go first.** Re-read the function and line references
  of the later one at its outline.
- **Overlaps with PLAN-LB-87 (parked)** on `_build_execute_factory.py`; if it is un-parked, run it in sequence.
- **Adjacent to** (left untouched): `_build_cli.py` (the in-process resolution error path, which is correct), `marshalld.py` and the
  daemon scheduler (LB-108's), and the lane's build routing text (`runbook-lane/SKILL.md`).
- **Running plans:** checked at emit by the disjointness gate; none were checked in this draft.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-112-routed-build-worktree-fault-truth.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
