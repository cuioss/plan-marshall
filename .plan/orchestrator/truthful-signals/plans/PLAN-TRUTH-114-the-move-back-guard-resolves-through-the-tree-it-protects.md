# PLAN-TRUTH-114: The move-back guard resolves through the tree it protects

epic: truthful-signals
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and hand-off contract.

## Provenance

Staged 2026-08-26 from an operator paste of a foreign-machine plan-marshall report, after that
machine lost a plan directory to `worktree-remove`. The report named the mechanism; every claim
below was re-corroborated first-party against the implementing source at `31bed3e76` before it was
recorded, and the corroboration found **two mechanisms the report did not name** (the audit-row
refutation, D2, and the pinned-resolver test blindness, D3).

This is a **recurrence**, not a first sighting: the epic already carries `leaf-validator-yield` as a
run where a hand-invoked `worktree-remove` lost the plan dir. That incident was closed as operator
error against a guard believed to be script-enforced. It was not operator error.

## Objective

**`worktree-remove`'s move-back precondition is resolved through the cwd it is protecting, so it
fails OPEN in exactly the geometry it exists to refuse.** `cmd_worktree_remove` gates on
`_plan_dir_on_current_checkout(plan_id)`, which walks up from cwd and probes
`{root}/.plan/local/plans/{id}/status.json`. When cwd is inside the worktree, the walk-up terminates
at the worktree, the probe finds the worktree-resident `status.json` — **the sole authoritative copy
the guard exists to protect** — concludes "the plan dir is on the current checkout", and permits the
removal that destroys it.

This is not a typo. The predicate's own docstring documents the resolution as intended
("an already-cwd-pinned worktree resolves to its own plan dir (`current`)"), because it was written
for a different caller. The guard is correct only when called from main, and no document states the
cwd at the call site.

Make the guard resolve main-anchored, refuse when cwd is inside the removal target, and reconcile the
three documents that currently advertise a protection the code does not provide.

### The verb's OTHER failure mode, folded in 2026-08-26 (D5/D6)

⛔⛔ **`cmd_worktree_remove` carries TWO defects with OPPOSITE polarity, and this plan now owns both.**
The guard above fails **OPEN** — it permits a removal that destroys plan state. The removal itself
fails **CLOSED** — it exceeds a fixed 60 s budget on a GB-scale worktree and refuses, retaining the
worktree. They are separate remedies with separate tests, and they are in one plan because they are in
one verb and because of the interaction below.

⭐⭐ **THE INTERACTION IS THE REASON THE ORDER MATTERS, AND IT MUST NOT BE LOST DURING
IMPLEMENTATION.** The guard is checked at `git-workflow.py`:1545; the `git worktree remove` runs at
:1558. When the guard fails open **and** the removal then times out, **nothing is destroyed** — the
worktree survives. ⇒ **The fail-closed timeout has been accidentally MASKING the fail-open guard.**
Landing D5/D6 without D0/D1 would make the destruction path strictly MORE reachable than it is today.
**D0 and D1 MUST land in the same change as, or before, D5** — never after. A partial ship that fixes
only the timeout is worse than shipping nothing.

⚠ This fold was an operator decision. The recorded counter-argument, preserved so a later reader sees
the trade rather than inferring it was unconsidered: it widens a spec whose subject is a data-loss
guard, and mixes a fail-open **correctness** fix with a fail-closed **performance** fix. The masking
interaction is what makes one plan defensible.

## Deliverables

**Seven deliverables — over the template's ~6 presumption, under this epic's raised split guard of 12
(operator decision 2026-08-08). Proceeding unsplit is recorded, not assumed:** D5/D6 were folded here
by operator direction 2026-08-26 because the two failure modes live in ONE verb and because the
fail-closed one has been MASKING the fail-open one (see § The verb's OTHER failure mode). Splitting
them would put the masking interaction across a plan boundary, where a partial ship makes the
data-loss path more reachable — the exact outcome the fold prevents.

1. **D0 — Resolve the move-back guard against the main checkout, not cwd.** `cmd_worktree_remove`'s
   precondition probe resolves through the sanctioned main-anchored exception the codebase already
   has (`resolve_main_anchored_path` / git-common-dir, ADR-002) rather than through
   `_find_plan_root_from_cwd`. Scope the change to the guard's own resolution: `_plan_dir_on_current_checkout`
   stays correct for `cmd_locate_plan_checkout`, whose contract genuinely is "is it on the CURRENT
   checkout" — so the fix is a guard-specific main-anchored predicate, not a redefinition of the
   shared one. `main_root` (the `git -C` target, git-workflow.py:1524) is the SECOND cwd-derived
   value at this call site and is fixed in the same change.
2. **D1 — Defence-in-depth: refuse when cwd is inside the removal target.** An independent refusal
   that does not depend on D0 being reasoned correctly, so the two failure modes are not both carried
   by one predicate.
3. **D2 — Re-derive the caller set the cwd-keyed audit asserted, and correct its row.**
   `cwd-keyed-store-resolution-audit.md` JUSTIFIES `_plan_dir_on_current_checkout` on the explicit
   ground that it feeds `cmd_locate_plan_checkout` and "never stands alone as authoritative absence".
   `cmd_worktree_remove` is a second caller the audit never enumerated, where the predicate DOES stand
   alone and the conclusion drawn from it IS a destructive authorization. Re-derive the caller set by
   enumeration and publish the population, per the epic's population-derived-detector rule.
4. **D3 — Regression test that can observe the failing geometry.** Every existing `worktree-remove`
   test overrides `_find_plan_root_from_cwd` to return `main` by fiat, so the suite structurally
   cannot see this defect. Add a matched pair: the same fixture geometry with the resolver reflecting
   a worktree cwd MUST refuse (`plan_dir_not_moved_back`), and the main-cwd case MUST still succeed.
5. **D5 — FOLDED 2026-08-26 (operator direction): the SAME verb also fails CLOSED, on a fixed 60 s
   budget.** `cmd_worktree_remove` calls `run_git(git_args)` with no timeout override, so it inherits
   `run_git`'s fixed `_DEFAULT_TIMEOUT_SECONDS = 60`. Measured at staging time: `git status` in a live
   worktree returns in **0.067 s**, so the cleanliness scan is NOT the cost — the **tree deletion** is,
   against **276,757 files / 1.0 GB** of `.plan/temp/pytest-basetemp` in the running plan's worktree
   (1.7 GB in another, 1.8 GB in main). ⛔ **Do not "fix" this by raising the constant** — a fixed
   budget over an unbounded tree fails again at the next size. The removal must either be budgeted
   from the observed tree size or delete the known-regenerable scratch before invoking git, and either
   way it must **report which it did**. ⭐ Recorded 5 times already (W-088-b twice, #1034 the third
   sighting) with the standing prediction *"this will recur and get worse"*; it has.
6. **D6 — the growth bound is on the WRONG DIMENSION, and the prose claims the bound it does not
   enforce.** `build.py` prunes `PYTEST_BASETEMP_ROOT` to `PYTEST_BASETEMP_KEEP = 3` **session
   directories**, ordered by mtime. That bounds the **count** of session dirs and **never their size**,
   so three retained sessions of ~90k files each is the steady state — exactly what was measured. ⛔ The
   defect is not the retention, which works as coded; it is that **two docstrings assert the stronger
   claim the code does not support** — *"keep `PYTEST_BASETEMP_ROOT` from growing without bound"*
   (`:114`) and *"so the directory cannot grow without bound"* (`:166`). ⇒ Bound the dimension that
   actually grows (total size or file count), or state the real invariant. **This is the epic's theme
   inside the build harness: a guard reporting `bounded` while bounding the wrong axis.**
7. **D4 — Reconcile the three documents with the fixed behaviour.** `branch-cleanup.md`:1497 asserts
   cwd-independence that is false at two points; `worktree-handling.md` § Cleanup Ordering item 0 and
   `branch-cleanup.md`:92 advertise a non-`--force`-overridable script enforcement that does not hold;
   `cwd-policy.md` leaves the cwd at this call site unstated. State it.

## Claim Labels

- OBSERVED: `cmd_worktree_remove` gates the move-back precondition on `_plan_dir_on_current_checkout(args.plan_id)` — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`:1545 § `cmd_worktree_remove`
- OBSERVED: `_plan_dir_on_current_checkout` resolves its root via `_find_plan_root_from_cwd()` and probes `{root}/.plan/local/plans/{id}/status.json` — read at `git-workflow.py`:1944 § `_plan_dir_on_current_checkout`
- OBSERVED: `_find_plan_root_from_cwd` walks up from `Path.cwd()` to the first ancestor containing `.plan/local` and returns it; there is no sideways resolution — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py`:374 § `_find_plan_root_from_cwd`
- OBSERVED: the predicate's docstring states the worktree-cwd resolution as INTENDED ("an already-cwd-pinned worktree resolves to its own plan dir (`current`)"), so the guard's failure is a caller/contract mismatch and not a defect in the predicate — read at `git-workflow.py`:1944 § `_plan_dir_on_current_checkout`
- OBSERVED: `main_root = _find_plan_root_from_cwd()` is a SECOND cwd-derived value at the same call site, used as the `git -C` target for `worktree remove` — read at `git-workflow.py`:1524 § `cmd_worktree_remove`
- OBSERVED: `branch-cleanup.md` asserts "The `worktree-remove` verb operates on the main checkout internally and does not rely on the caller's cwd", which is false at both cwd-derived points above — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`:1497
- OBSERVED: the refusal is advertised as script-enforced and NOT overridable by `--force` in two documents, which is why a caller trusts the ordering rather than double-checking it — read at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md` § "Cleanup Ordering: Worktree First, Then Branch" item 0, and `branch-cleanup.md`:92
- OBSERVED: `cwd-policy.md` states the phase-5+ invariant as "the working directory is never changed away from the pinned worktree" while also stating the move-back `integrate_into_main.py` "runs with cwd = main"; neither statement fixes the cwd at the `worktree-remove` call site, which sits between them — read at `marketplace/bundles/plan-marshall/skills/tools-script-executor/standards/cwd-policy.md`:19 and :23
- OBSERVED: the cwd-keyed audit JUSTIFIES `_plan_dir_on_current_checkout` naming exactly one caller (`cmd_locate_plan_checkout`) and reasoning only about a `False` standing alone as authoritative absence; the `cmd_worktree_remove` failure is the mirror polarity — a `True` standing alone as authoritative presence — read at `marketplace/bundles/plan-marshall/skills/manage-locks/standards/cwd-keyed-store-resolution-audit.md`:55
- OBSERVED: every existing `worktree-remove` test pins the resolver by fiat — `monkeypatch.setattr(git_workflow, '_find_plan_root_from_cwd', lambda: main)` — including the refusal case and the `--force` case, so the suite proves the guard only under the main-cwd assumption — read at `test/plan-marshall/workflow-integration-git/test_git_workflow.py`:1494 § `TestWorktreeRemoveMoveBackPrecondition._patch`, and `test/plan-marshall/workflow-integration-git/test_git_workflow_worktree.py`:432 § `TestWorktreeRemove.test_remove_drops_worktree_then_branch`
- OBSERVED *(D5)*: `cmd_worktree_remove` invokes `run_git(git_args)` with no timeout argument, inheriting the module default — read at `git-workflow.py`:1558 § `cmd_worktree_remove`, and `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git_provider.py`:33 § `run_git` (`timeout: int = _DEFAULT_TIMEOUT_SECONDS`, documented as "a default 60s timeout")
- OBSERVED *(D5)*: the cleanliness scan is not the cost — `git -C {worktree} status --porcelain` returned in **0.067 s** on a live worktree, measured 2026-08-26 at `91a07aaa4`
- OBSERVED *(D5)*: the deletion is the cost — the running plan's worktree holds **276,757 files / 1.0 GB** under `.plan/temp/pytest-basetemp`; a second worktree holds 1.7 GB, a third 1.1 GB, and the main checkout 1.8 GB. Measured 2026-08-26 by `find … | wc -l` and `du -sh`
- OBSERVED *(D6)*: `PYTEST_BASETEMP_KEEP = 3` and `_prune_basetemp_roots` sorts session dirs by mtime and `rmtree`s everything past index 3 — a bound on the COUNT of session dirs, with no size or file-count term anywhere in the function — read at `build.py`:112-150 § `PYTEST_BASETEMP_ROOT`, `PYTEST_BASETEMP_KEEP`, `_prune_basetemp_roots`
- OBSERVED *(D6)*: two docstrings assert an unbounded-growth guarantee the count-bound does not provide — *"prune here to keep `PYTEST_BASETEMP_ROOT` from growing without bound"* (`build.py`:114) and *"so the directory cannot grow without bound"* (`build.py`:166); the measured root holds exactly 3 session dirs, so the retention is working as coded and the claim is still false
- OBSERVED *(D5/D6)*: the epic ledger records this timeout 5 times without an owner — W-088-b (two timeouts in one landing, with the standing prediction *"the 60 s budget is FIXED and the scratch grows with the test suite — this will recur and get worse"*) and a third sighting at #1034 — read at `epic.md` § Watches "From the 2026-08-24 PLAN-TRUTH-088 drain" and § Open Defects
- HYPOTHESIS *(D5)*: no staged spec in ANY epic owned this before the fold — a `grep` for `pytest-basetemp` and the 60 s budget across `.plan/local/orchestrator/*/plans/` returned nothing. Confirm/refute by re-running that sweep at outline; ⛔ **a zero from a path-scoped grep is not a derived population** (verify-at-outline)
- HYPOTHESIS: the foreign machine's loss occurred with cwd inside the worktree at the `worktree-remove` call, rather than through a distinct mechanism — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` § the `worktree-remove` call site, by establishing what pins cwd between the Step 0 move-back and branch-cleanup (verify-at-outline)
- HYPOTHESIS: `git worktree remove` issued with `-C {worktree}` against `{worktree}` itself fails rather than succeeding, which would mean the guard's fail-open is caught downstream by git in SOME geometries and not others — confirm/refute at `git-workflow.py`:1558 § `cmd_worktree_remove` git invocation (verify-at-outline). ⛔ This does not soften D0/D1: a destructive authorization that depends on a downstream tool's incidental refusal is not a guard.
- Verify-first clause: before scoping D0, confirm that `resolve_main_anchored_path` is reachable from `git-workflow.py` without introducing a new sideways resolver, and that using it here falls inside ADR-002's sanctioned exception set rather than widening it. Refutation loops back and re-scopes D0 toward an explicit `--project-dir`-style caller-supplied main root.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`:1504 — `cmd_worktree_remove`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`:1944 — `_plan_dir_on_current_checkout`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py`:1964 — `cmd_locate_plan_checkout` (the caller whose contract must NOT change)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/marketplace_paths.py`:374 — `_find_plan_root_from_cwd`, and the main-anchored resolver section below it
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/standards/worktree-handling.md` — § "Cleanup Ordering: Worktree First, Then Branch" item 0
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md`:92, :1497
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/standards/cwd-policy.md`:19, :23
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-locks/standards/cwd-keyed-store-resolution-audit.md`:55
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_git_workflow.py`:1453 — `TestWorktreeRemoveMoveBackPrecondition`
- OBSERVED: `test/plan-marshall/workflow-integration-git/test_git_workflow_worktree.py`:413 — `TestWorktreeRemove`
- HYPOTHESIS: `test/plan-marshall/workflow-integration-git/test_worktree_move_lifecycle.py` — the move-in/move-out lifecycle suite may carry the same pinned-resolver assumption (verify-at-outline)
- OBSERVED *(D5)*: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git_provider.py`:29 — `run_git`, and its `_DEFAULT_TIMEOUT_SECONDS` constant
- OBSERVED *(D6)*: `build.py`:108-170 — `PYTEST_BASETEMP_ROOT`, `PYTEST_BASETEMP_KEEP`, `_prune_basetemp_roots`, `_prepare_session_basetemp`
- HYPOTHESIS *(D5)*: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/branch-cleanup.md` — the `worktree_remove_failed` error-handling branch may need a distinct timeout disposition, since "the worktree has uncommitted changes" and "the removal exceeded its budget" are currently one error code (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none. The defect is live in merged main and independent of every queued plan.
- Overlaps with: none among the live queue. `git-workflow.py` and `marketplace_paths.py` are touched
  by no other staged spec; `cwd-keyed-store-resolution-audit.md` is `manage-locks` documentation and
  no live spec declares it.
- Adjacent to: `PLAN-TRUTH-109` (`manage-findings` store resolution) — the same ADR-002 cwd-vs-main
  tension, in a different component, with a read-side rather than destructive consequence. They stay
  separate because the remedies differ: `-109` needs an absent-vs-empty discriminator, this needs a
  main-anchored resolution at one guard. ⭐ If both land, the pair is the evidence for a standing rule
  about which resolver a *destructive* precondition may use.
- Adjacent to: `PLAN-TRUTH-113` (declared surface wrong in both directions) — this spec's Expected
  Surface is deliberately path-and-symbol exact so it is usable as a positive control for `-113` D0.

## Priority

⛔ **This is a live data-destruction path in merged main with a known prior incident.** It is the only
queued item whose failure mode is unrecoverable loss rather than a misleading signal, and it should
be considered for the queue head ahead of queue order once the running plan lands.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/truthful-signals/plans/PLAN-TRUTH-114-the-move-back-guard-resolves-through-the-tree-it-protects.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits
NO file under `.plan/local/orchestrator/` other than its own `inbox/{sender}-{seq}` message — the
orchestrator owns every other ledger write — and reports its outcome through its PR and its inbox
message. The inbox exception's qualifiers and the sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
