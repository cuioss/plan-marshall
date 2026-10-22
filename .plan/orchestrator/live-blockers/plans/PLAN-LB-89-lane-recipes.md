# PLAN-LB-89: The runbook lane gives a base-sha evidence recipe and a thread-reply recipe, and a test bootstrap cannot rewrite another checkout's executor

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-89-lane-recipes.md` and is queued as one row file, `queue/PLAN-LB-89.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the adversarial landing analysis of PLAN-LB-79 (#1835, `d60b36f8d`),
> `landings/PLAN-LB-79.md` § Report Contradictions 2, 4 and 5 and § Code Defects C9. Priority is
> **medium**: the lane works without it, but PLAN-LB-79 improvised each of these, broke rules doing so,
> and put a false premise to the operator. **Each deliverable is its own outline deliverable, and each
> Done-when is its own success criterion. Do not merge them.** A Done-when says "fails at `d60b36f8d`"
> only where the behaviour is new at that sha; a clause that already holds says "holds at `d60b36f8d`";
> and no Done-when is labelled "holds at" while a claim it rests on is still a HYPOTHESIS below. Grade each
> deliverable against THIS spec's Done-when text; an outline that rewrites a Done-when must say so and why.

## Objective

A Done-when that says "fails at the base sha" needs a run at the base sha, and the runbook lane gives no
way to get one. PLAN-LB-79 created a git worktree and then a local clone inside `.plan/temp`, ran the
test suite from the clone, edited the clone's `conftest.py`, regenerated the executor by hand, and tried
`git clean` to remove what it had made. The clone's test bootstrap rewrote an executor, the executor was
left without a version stamp, the lane misread the result as "162 scripts under the clone" and asked the
operator a question built on that misreading, and the only copy of the evidence it cites by path is an
untracked file in the clone. The same run did not know the flag that selects a thread reply on the CI
abstraction and wrote reply bodies straight into a plan-less work directory. This plan gives the lane the
two recipes, and stops a test bootstrap from writing outside the checkout it runs in.

## Deliverables

1. **The lane text gives one base-sha evidence recipe that needs no clone and leaves its evidence in git or in the PR.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - The lane names the sanctioned way to obtain a failing run at the base sha (a detached worktree
     created through the git workflow verbs, built and tested through the build seam, removed with the
     same verbs before the landing). A `git clone`, a raw `git worktree add` into `.plan/temp`, a hand-run
     `generate_executor` and an edit of a test harness file in the base copy are named as not allowed.
     Decide at outline which git workflow verb creates the base worktree (HYPOTHESIS below), and record why.
   - The base evidence is an artifact that survives the base copy: the failing log identifier and the
     file that produced it are recorded in the PR body, and a probe file the Done-when cites by path is
     committed (under the plan's test tree) or its content is placed in the PR body; a path that exists
     only in the removed base copy is not evidence.
   - The base worktree is removed before the landing is written, or the landing reports it as owed
     cleanup with `cleanup_owed=true`; the lane never asks the operator how to delete what it created
     without first stating what exists, read from the tree.

   *Done when:* each of these fails at `d60b36f8d`:
   - doc tests assert the lane text names the recipe, names the four disallowed forms, and states where
     the evidence lives;
   - a doc test asserts the landing section requires the base-copy removal or the owed-cleanup fact and
     forbids an operator question about it that is not preceded by a read of the tree.

2. **A test bootstrap run from another checkout cannot rewrite that checkout's executor, and an unversioned executor is named.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - `test/conftest.py` `_ensure_executor_present` writes `.plan/execute-script.py` only under the project
     root derived from its own location, and refuses when the generator's target resolves outside it.
   - `generate_executor` reports an executor whose `MARSHALL_VERSION` it could not stamp as `unversioned`
     in its result instead of writing an empty string silently, and `cleanup restart-check`'s
     `registry_parity` row names that cause rather than only "could not be read (empty)".
   - Verify first (HYPOTHESIS below): the bootstrap from a clone is what wrote the main executor.

   *Done when:* each of these fails at `d60b36f8d`:
   - a bootstrap test run with the working directory in a clone and the main checkout's `PLAN_BASE_DIR`
     in the environment writes nothing under the main checkout's `.plan/`;
   - `generate_executor` for an unresolvable version returns `unversioned` and a `restart-check` fixture
     with an empty `MARSHALL_VERSION` names it.

3. **The lane text names the flag that selects a thread reply, and the CI abstraction names it when a body of the wrong kind is refused.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - The lane's review-comment step states `ci pr prepare-comment --for thread-reply` for an inline thread
     reply (the default is `reply`), and that a body is allocated by `prepare-comment`, never written
     into `.plan/local/plans/NO_PLAN/work/ci-bodies/` by hand.
   - `ci pr thread-reply` given a `pr-reply` body refuses with a message that names `--for thread-reply`.

   *Done when:* each of these fails at `d60b36f8d`:
   - a doc test asserts the lane text carries the flag and the no-hand-written-body rule;
   - a unit test shows the refusal text for a wrong-kind body contains `--for thread-reply`.

Split guard: three deliverables.

## Claim Labels

- OBSERVED: the PLAN-LB-79 root session ran `git worktree add .plan/temp/base-probe origin/main --detach` (17:48:40), removed it with `--force` (17:52:33), ran `git clone --local … .plan/temp/base-clone` (17:52:44), ran `generate_executor generate` by hand (17:53:13), edited the clone's `conftest.py` (17:55:39) and tried `git clean -ndx` (denied) — orchestrator re-query of the session store (`ses_ea078fef6ffe…`).
- OBSERVED: the main executor has 330 entries, none containing `base-clone`, and `MARSHALL_VERSION = ''` — orchestrator read of `.plan/execute-script.py` at `d60b36f8d`; `cleanup restart-check` reports `registry_parity: indeterminate`, "the executor version could not be read (empty)".
- OBSERVED: `test_guard_documentation_sweep_base_probe.py`, cited by the PR as the D4 base evidence, is in no commit and exists only in `.plan/temp/base-clone` — corroboration read (`git log --all` empty).
- OBSERVED: `ci pr prepare-comment` takes `--for {reply,thread-reply}` with default `reply`, and `thread-reply` consumes a `pr-thread-reply` body — `tools-integration-ci/scripts/ci_base.py` L1491-1497 and `workflow-integration-github/scripts/_github_pr.py` L3397, L1570 (corroboration read, not re-read).
- OBSERVED: the run wrote five `pr-thread-reply-thread-{1..5}.md` bodies directly into `.plan/local/plans/NO_PLAN/work/ci-bodies/` (11:52-11:54) — orchestrator re-query of the session store.
- HYPOTHESIS: the clone's `conftest.py` `_ensure_executor_present` (`test/conftest.py` L154-249) wrote the MAIN checkout's executor at about 17:54, through an environment value or a cwd that named the main checkout — confirm at `test/conftest.py` and `generate_executor.py` before D2 scopes; the corroboration's reading of the timeline, not re-read (verify-at-outline).
- HYPOTHESIS: `workflow-integration-git` offers a worktree-create verb that accepts a detached ref and a name outside the plan-worktree convention — confirm at `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` (verify-at-outline) (D1).
- Verify-first clause: decide the base worktree's verb and location (D1) and whether the bootstrap write is a conftest or a generator defect (D2) before either is scoped; record why.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — the evidence-order section, the review-comment step, the landing section (D1, D3)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the doc tests (D1, D3)
- OBSERVED: `test/conftest.py` — `_ensure_executor_present` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-orchestrator/scripts/orchestrator.py` — `_registry_parity_signal` evidence text (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/ci_base.py` and `marketplace/bundles/plan-marshall/skills/workflow-integration-github/scripts/_github_pr.py` — the refusal text (D3)
- OBSERVED: `test/plan-marshall/tools-integration-ci/` and `test/plan-marshall/tools-script-executor/` and `test/plan-marshall/plan-orchestrator/` (D2, D3)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/git-workflow.py` — read only unless the base worktree needs a new verb (verify-at-outline) (D1)

## Dependencies and Sequencing

- Depends on: PLAN-LB-79 (shipped, `d60b36f8d`).
- Overlaps with: PLAN-LB-73 on `runbook-lane/SKILL.md` and `test_runbook_lane.py` (D4's §0a re-read rule and §8 landing honesty, and D1 §3 and §6), PLAN-LB-85 on the same two files (the §6 read step). Sequence this plan after PLAN-LB-73; the emit gate decides. PLAN-LB-87 touches `_build_execute_factory.py`, not a file here.
- Adjacent to: PLAN-LB-88, which owns the guard and hook; this plan does not edit them.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-89-lane-recipes.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
