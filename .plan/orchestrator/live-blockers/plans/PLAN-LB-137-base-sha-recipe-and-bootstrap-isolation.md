# PLAN-LB-137: The runbook lane gives a base-sha evidence recipe and a thread-reply recipe, and a test bootstrap cannot rewrite another checkout's executor

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-137-base-sha-recipe-and-bootstrap-isolation.md` and is queued as one row file, `queue/PLAN-LB-137.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Regrouped on the operator's word of 2026-11-09 from the parked PLAN-LB-89 (the adversarial analysis of PLAN-LB-79, #1835,
> `d60b36f8d`). Every claim was re-grounded against `main` at `9cd644892` by a read-only leaf on 2026-11-09; PLAN-LB-116 (`5eb2f9d9d`)
> added 240 lines to `runbook-lane/SKILL.md`, so every old line reference is stale. The bootstrap defect is worse than the old spec
> said: the generator writes the MAIN checkout's executor even without an environment variable. **Each deliverable is its own outline
> deliverable, and each Done-when is its own success criterion. Do not merge them.** Every Done-when below fails at `9cd644892`
> unless it says "holds at". No Sonar. No token or measurement work.

## Objective

A Done-when that says "fails at the base sha" needs a run at the base sha, and the lane gives no way to get one: PLAN-LB-79 made a
git worktree, then a local clone inside `.plan/temp`, ran the suite from the clone, edited the clone's `conftest.py`, regenerated the
executor by hand and tried `git clean`. The clone's test bootstrap overwrote the main checkout's executor, which was left without a
version stamp, the lane misread the result and put a false premise to the operator, and the only copy of the evidence it cites by path
was an untracked file in the clone. The same run did not know the flag that selects a thread reply. This plan gives the lane the two
recipes and stops a bootstrap from writing outside its own checkout.

## Deliverables

1. **The lane text gives one base-sha evidence recipe that needs no clone and leaves its evidence in git or in the PR.**
   - The lane (`runbook-lane/SKILL.md` §1 Evidence L366-385 or §3 step 2 L550, which only says "capture their evidence under the
     `order` §1 defines") names the sanctioned way to obtain a failing run at the base sha: a detached base worktree, built and tested
     through the build seam, removed before the landing is written (the lane already uses a raw `git worktree remove` at cleanup,
     L900-902, because `worktree-remove` refuses in this lane). A `git clone`, a raw `git worktree add` into `.plan/temp`, a hand-run
     `generate_executor` and an edit of a harness file in the base copy are named as not allowed.
   - The base evidence is an artifact that survives the base copy: the failing log identifier and the file that produced it are in
     the PR body, and a probe file a Done-when cites by path is committed under the plan's test tree or its content is in the PR body;
     a path that exists only in the removed base copy is not evidence. The base worktree is removed before the landing is written, or
     the landing reports `cleanup_owed=true`; the lane never asks the operator how to delete what it created without first stating
     what exists, read from the tree.
   - Decide at outline which verb creates the base worktree and record why. `worktree-create` (`git-workflow.py` L4056-4076, `cmd_worktree_create`
     L2472+) takes a required `--plan-id` and `--branch` and an optional `--base`, always creates a branch under
     `worktree_root/plan_id` (L2518) and generates its own executor; there is no `--detach` and no free name. Either a `--detach` mode
     is added (no branch; a `{plan}-base` name), in which case an executor regeneration is owed and the landing says so, or the
     recipe names a raw sanctioned form.

   *Done when:* each of these fails at `9cd644892`, in `test/plan-marshall/runbook-lane/test_runbook_lane.py`: a doc test asserts the
   lane text names the recipe, the four disallowed forms and where the evidence lives; a doc test asserts the landing section requires
   the base-copy removal or the owed-cleanup fact and forbids an operator question about it that is not preceded by a read of the
   tree. If a `--detach` mode is added, a test in the `workflow-integration-git` tests directory (enumerated at outline) creates a
   detached worktree and finds no branch.

2. **A test bootstrap run from another checkout cannot rewrite that checkout's executor, and an unversioned executor is named.**
   - `test/conftest.py` `_ensure_executor_present` (L154-246) checks `PROJECT_ROOT/.plan/execute-script.py`
     (`PROJECT_ROOT = TEST_ROOT.parent`, the clone's root) and runs `generate_executor.py generate` with `cwd=project_root` and no
     `env=` (L212-227), so it inherits `PLAN_BASE_DIR`. The generator writes to `executor_path()` = `get_tracked_config_dir()/execute-script.py`
     (`generate_executor.py` L243-245), resolved by `file_ops.py` L1475-1505 in the order `PLAN_TRACKED_CONFIG_DIR`, `PLAN_BASE_DIR`,
     then the nearest ancestor of the cwd holding `.plan/local` (`marketplace_paths.py` L560-579). With the main checkout's
     `PLAN_BASE_DIR` set it writes MAIN's executor; even without it, a clone under main's `.plan/temp/` has no `.plan/local`, the
     walk-up reaches the main checkout and the write replaces main's executor with the clone's script surface; the post-check
     (L240-246) then raises, after the write has happened.
   - The bootstrap passes an `env` with `PLAN_BASE_DIR` and `PLAN_TRACKED_CONFIG_DIR` removed and pins the output to its own
     `project_root`, or the generator refuses to write outside the checkout of its cwd; decide at outline which defect owns it (the
     conftest, the generator, or both) and record why.
   - `generate_executor` stamps an executor whose version it could not read as `unversioned` and reports why, instead of the empty
     string `newest_version` returns (L1720-1733; the template line is `MARSHALL_VERSION = '{{GENERATED_VERSION}}'`, template L86,
     substituted at L2126). `_registry_parity_signal` (`plan-orchestrator/scripts/orchestrator.py` L5546-5551) names that cause
     instead of "could not be read (empty)" (`plugin_registry.py` L100 `EXECUTOR_VERSION_EMPTY`).

   *Done when:* each of these fails at `9cd644892`: the bootstrap run with the working directory under a directory whose ancestor has
   `.plan/local`, and again with `PLAN_BASE_DIR` set to a sentinel directory, writes nothing outside its `project_root`, in
   `test/plan-marshall/tools-script-executor/test_generate_executor_bootstrap.py`; `generate_executor` for an unresolvable version
   returns `unversioned` and a `restart-check` fixture with an empty `MARSHALL_VERSION` names the cause, in
   `test/plan-marshall/plan-orchestrator/test_orchestrator_restart_check_registry_parity.py`.

3. **The lane text names the flag that selects a thread reply, and the CI abstraction names it when a body of the wrong kind is refused.**
   - The lane's §6 step 2 (L723-724) says only "`ci pr prepare-comment` + `ci pr reply`"; §6 step 5 (L779-783) names `ci pr thread-reply`
     and never `--for thread-reply`; §1 (L402-404) permits writing into `.plan/local/plans/NO_PLAN/work/ci-bodies/` slots "that step 6
     prescribes" and does not forbid hand-writing a body there. The text states `ci pr prepare-comment --for thread-reply` for an
     inline thread reply (the default is `reply`, `ci_base.py` L1491-1497) and narrows the §1 permission to a path a `prepare-*` verb
     returned.
   - `ci pr thread-reply` given only a `pr-reply` body returns `body_not_prepared` (`ci_base.py` L315-328) naming `prepare-body`; the
     refusal maps each kind to its prepare command (`pr-thread-reply` to `ci pr prepare-comment --for thread-reply`). The provider
     wraps the message unchanged (`_github_pr.py` L1802-1803); the GitLab sibling is read at outline.

   *Done when:* each of these fails at `9cd644892`: a doc test in `test_runbook_lane.py` asserts the lane text carries `--for
   thread-reply` and the no-hand-written-body rule; the `body_not_prepared` message for kind `pr-thread-reply` contains `--for
   thread-reply`, in `test/plan-marshall/tools-integration-ci/test_ci_base_primitives.py`. The existing pins of `body_not_prepared`
   in `test_github_ops_errors.py` and `test_gitlab_ops_errors.py` are updated, not loosened.

Split guard: three deliverables, each independent. D2 is on the test bootstrap and the generator and splits off first for review size.

## Standing Constraints

- Settle each HYPOTHESIS first. A refuted claim is dropped from its deliverable and the PR says so.
- A bootstrap or generator never writes outside the checkout it runs in; a refusal is a named reason.
- Documentation states the current behaviour; no comment or document describes a change or the old behaviour.
- Tests state their purpose, use the `PLAN_MARSHALL_HOME` fixture and are shown red where a Done-when says so.
- Executor regeneration is owed if D1 adds a verb flag; the landing says so.
- No token or measurement work. No Sonar.

## Claim Labels

- OBSERVED: the lane has no base-sha recipe: §1 (`runbook-lane/SKILL.md` L366-385) defines `test-first` as "seen failing against the unfixed code" and nowhere forbids a clone, a raw `git worktree add` into `.plan/temp`, a hand-run `generate_executor` or a harness-file edit in the base copy; the lane uses a raw `git worktree remove` at cleanup (L900-902)
- OBSERVED: `cmd_worktree_create` has no `--detach` (`workflow-integration-git/scripts/git-workflow.py` L4056-4076, L2472+, path at L2518, reserved ledger key refused at L2505-2515)
- OBSERVED: `_ensure_executor_present` (`test/conftest.py` L154-246) inherits the environment (L212-227); the generator and the resolver chain are as cited in D2; `newest_version` returns `''` when nothing is readable (`generate_executor.py` L1720-1733) and no `unversioned` sentinel exists
- OBSERVED: `--for {reply,thread-reply}` (default `reply`) at `tools-integration-ci/scripts/ci_base.py` L1491-1497; the kind mapping at `workflow-integration-github/scripts/_github_pr.py` L3626-3629; `pr thread-reply` consumes `BODY_KIND_PR_THREAD_REPLY` (L1801); the refusal at `ci_base.py` L315-328 names `prepare-body`
- OBSERVED: the PLAN-LB-79 root session ran `git worktree add .plan/temp/base-probe origin/main --detach`, removed it with `--force`, ran `git clone --local … .plan/temp/base-clone`, ran `generate_executor generate` by hand, edited the clone's `conftest.py` and tried `git clean -ndx` (denied) — re-query of the session store at the time; the main executor then had 330 entries and `MARSHALL_VERSION = ''`
- HYPOTHESIS: a detached worktree can be built and tested through the build seam under a `{plan}-base` name without the plan-worktree convention getting in the way — confirm at `git-workflow.py` and the build-server project resolution (verify-at-outline, D1)
- HYPOTHESIS: the GitLab provider's `body_not_prepared` message needs the same mapping — confirm at `workflow-integration-gitlab` (verify-at-outline, D3)
- Verify-first clause (D1): decide the base worktree's verb and location; record why.
- Verify-first clause (D2): reproduce the write outside the checkout as a fixture at `9cd644892` before editing; decide whether it is a conftest or a generator defect and record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — §1, §3 step 2, §6 steps 2 and 5, the landing section (D1, D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the doc tests (D1, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — only if a `--detach` mode is added (verify-at-outline) (D1)
- OBSERVED: `test/conftest.py` — `_ensure_executor_present` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `_registry_parity_signal` evidence text (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` — the `body_not_prepared` message (D3)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_generate_executor_bootstrap.py` and `test/plan-marshall/tools-script-executor/test_generate_executor_behavior.py` (D2)
- OBSERVED: `test/plan-marshall/plan-orchestrator/test_orchestrator_restart_check_registry_parity.py` (D2)
- OBSERVED: `test/plan-marshall/tools-integration-ci/test_ci_base_primitives.py` (D3)
- OBSERVED: `test/plan-marshall/workflow-integration-github/test_github_ops_errors.py` and `test/plan-marshall/workflow-integration-gitlab/test_gitlab_ops_errors.py` — the pins of `body_not_prepared` (D3)

## Dependencies and Sequencing

- Depends on: PLAN-LB-79 (shipped, `d60b36f8d`); PLAN-LB-116 (shipped, `5eb2f9d9d`) is in the base.
- Overlaps with: PLAN-LB-129 on `runbook-lane/SKILL.md` only if it edits the `review-gate` section (sequence this plan after it); PLAN-LB-138 D3 on `runbook_lane.py` (not a file here).
- Adjacent to: the guard and hook (owned by PLAN-LB-88, not edited here).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-137-base-sha-recipe-and-bootstrap-isolation.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
