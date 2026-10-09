# PLAN-LB-33: Step tooling: a dispatched step can run the tests it changed, and the main executor survives a removed worktree

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-33-leaf-test-scope-and-executor.md` and is queued as one row file, `queue/PLAN-LB-33.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged on 2026-10-09 by operator instruction ("stage both"), from two Open Defects of this epic.
> Every OBSERVED claim below was read at HEAD `fcd54e6ef`.

> WEAK MERGE. The two halves share a subject (tooling every dispatched step depends on) and no
> file. They are one plan because each landing in this epic has cost 13 to 17 million tokens with
> more than half of it in finalize, so two small plans would pay that overhead twice. The outline
> is licensed to split them back into two plans along the line between deliverables 6 and 7.

## Objective

Two tooling defects cost plans in this repository far more than the work they interrupt.

**A dispatched step cannot run the tests it just changed.** Before a task's tests run, the step
asks which test target covers the changed paths. The resolver knows only paths under
`marketplace/bundles/` and test directories named after a bundle. For anything else — the
harness targets under `marketplace/targets/`, the test trees `test/marketplace/`,
`test/sync-harnesses/` and eight more — it returns no target, and the step falls back to the
whole-tree test run. Even where it does return a module, the module-wide run of the largest
bundle takes longer than a dispatched step may run. Either way the step stops and hands the run to
the main session. On PLAN-LB-29, 11 of 17 execute dispatches ended that way, at 3.9 million
tokens, each one reloading its context; on PLAN-LB-23, 5 of 7, and three test failures surfaced
only at batch runs because no step had run the tests it wrote. The same test files ran in 15 to
32 seconds when called by directory. The narrow target exists and the build wrapper accepts it;
the resolver does not offer it, and a narrow target that was never measured is classed as too
long by default.

**The main checkout's executor can be left pointing into a worktree that no longer exists.**
The generated `.plan/execute-script.py` embeds absolute paths to the script directories it was
generated from. A generation whose sources are a plan worktree writes its output wherever the
working directory resolves, so run from the main checkout it overwrites main's executor with
paths into the worktree. When that worktree is removed, every script call from the main checkout
fails at import. The recovery that should catch this looks for the plugin cache one directory
level too high and finds nothing, and there is no fallback to the checkout's own sources. A
second defect in the same file: the executor drops every empty-string argument, so the documented
call that clears a list fails.

This plan gives the resolver every target the wrapper accepts and a narrow unit for long modules,
lets a step run that unit inline, binds a generated executor to the checkout it is written into,
and makes the bootstrap recover or say what to run.

## Deliverables

1. **Every test tree the build wrapper accepts is a target the resolver can return.** The
   resolver's registered targets are bundle names only, while `build.py` accepts any directory
   under `test/` as a `module-tests` target. Derive the registered targets from the same source the
   wrapper uses — the directories under `test/` that hold tests — so a changed path under
   `test/sync-harnesses/` resolves to `sync-harnesses`. Shared fixture trees stay shared
   infrastructure. *Done when:* a test passes one changed path from each non-bundle test tree
   that holds tests and reads a non-null target for each; a path under `test/_shared/` still
   yields `divergence_possible: true`; the existing bundle cases are unchanged.

2. **Source paths outside the bundles resolve to the tests that cover them.** A changed file
   under `marketplace/targets/` matches neither arm of the resolver and is reported unresolved,
   which forces the whole-tree run. Resolve such a path through a declared source-to-test
   mapping, read from one place; the verify-first clause below settles whether that place is the
   project mapping list PLAN-LB-29 added for the module-mapping check. A source path with no
   mapping stays unresolved and says so by name. *Done when:* a test resolves
   `marketplace/targets/sync.py` to the `marketplace` test target; a source path with no mapping
   appears in `unresolved_paths` and keeps `divergence_possible: true`; the mapping is stated
   once and both its readers are tested against the same fixture.

3. **A long module offers a narrower unit.** When the footprint resolves to one module, the
   resolver also returns the sub-directories of that module's test tree that correspond to the
   changed paths (for a changed `skills/build-server/…` file, `plan-marshall/build-server`), and
   for changed test files the files themselves, as a list separate from `recommended_target`.
   It claims nothing it cannot derive: a changed path with no corresponding test directory
   contributes no narrow unit and is named. *Done when:* a test with a footprint inside one
   skill of the largest bundle reads that skill's test directory as the narrow unit; a footprint
   spanning three skills reads three; a footprint whose skill has no test directory reads none
   for it and names it; `recommended_target` is unchanged in all three.

4. **A narrow target that was never measured is not treated as too long.** The tier comes from
   a learned duration keyed on the full command string, so `module-tests
   plan-marshall/build-server` has its own key, starts unmeasured, and resolves to the
   orchestrator tier on its first use — which sends the step back to the main session for a
   20-second run. Give an unmeasured narrow target a bound derived from what is known: it is a
   subset of its module, so it can take no longer than the module's measured duration. When that
   bound is under the per-call ceiling the target is `per_task`; when the module itself is
   unmeasured or over the ceiling, apply a stated default for a single test directory and enforce
   it as a real timeout, so a wrong guess ends as a truthful `timeout` and not as a hung step.
   *Done when:* tests show an unmeasured sub-directory target of a measured, short module
   resolves `per_task`; of an over-ceiling module, `per_task` with the stated default bound; a
   run that exceeds that bound returns `timeout` with the bound and its source named, and its
   duration is learned so the next resolve is measured.

5. **A step runs the narrow unit inline and defers only the module-wide run.** `execute-task`
   Step 5b scopes to `recommended_target` or runs whole-tree, and `phase-5-execute` tells the leaf
   it must not run an orchestrator-tier step; neither tells it to try a narrower run first.
   State the order in both: resolve the scope; run the narrow units inline when they resolve
   `per_task`; hand back only the module-wide or whole-tree run, and say in the hand-back which
   narrow units already ran green. A task criterion of the form "must be observed failing before
   the source change" is met on the narrow unit. *Done when:* a doc-contract test asserts both
   documents state the order and name the same resolver fields; a cold reader given only the
   amended Step 5b answers "run the narrow unit inline, then hand back the module-wide run" to
   "the module test command resolves to the orchestrator tier and the resolver lists one narrow
   unit — what do you do?".

6. **The gates that share the resolver do not loosen.** The push freshness check derives the
   coverage a change requires from the same resolver, and the pre-push gate mirrors it. Widening
   what the resolver can name must not let a narrower build stand in for a wider one. Narrow
   units are advisory for the step and are never an input to the freshness check; a newly
   resolvable target changes the required coverage only where today's answer was "unresolved,
   therefore whole-tree", and each such change is listed. *Done when:* the existing freshness
   controls pass unchanged; a new control shows a change under `marketplace/targets/` plus a
   green narrow-unit row alone is still refused; the PR body lists every footprint shape whose
   required coverage differs from before, with the old and the new answer.

7. **A generation writes only the executor of the checkout its sources come from.**
   `--marketplace-root` pins where scripts are discovered; the output path comes from the working
   directory. Two callers pin the working directory themselves for exactly this reason, and one
   documented call does not. Make the generator safe regardless of the caller: when the
   discovery root lies in one checkout and the output path resolves into another, refuse with a
   distinct error that names both, and write nothing. *Done when:* a test generates with a
   worktree as discovery root from a working directory in the main checkout and reads the
   refusal, with main's executor byte-identical before and after; the same call from inside the
   worktree succeeds and embeds worktree paths; the two callers that pin the working directory
   still pass their tests.

8. **The bootstrap recovers from a missing script directory, or says what to run.** The
   recovery walks `{cache_root}/{version}/skills/{skill}/scripts`, while the installed layout is
   `{cache_root}/{bundle}/{version}/skills/{skill}/scripts`, so it finds nothing; and when a
   pinned directory is gone and no cache directory is found, the next import fails with
   `ModuleNotFoundError`. Fix the walk to the installed layout; add the checkout's own
   `marketplace/bundles` tree as a recovery source when the executor sits in a checkout that has
   one; and when nothing is found, exit with one message that names the missing directory and the
   regeneration command. *Done when:* a test generates an executor from a worktree, removes the
   worktree and runs the executor from a checkout that has the sources — the call succeeds; the
   same with no sources and no cache exits non-zero with the message and no traceback; a test
   against a fixture in the installed cache layout finds the newest version's directory.

9. **An empty argument value reaches the script.** The executor removes every empty-string
   argument "defensively", so `manage-references set-list --values ""`, the documented way to
   clear a list, loses its value and argparse exits 2. Keep an empty string that is the value of
   the option before it; the verify-first clause settles what, if anything, is still dropped.
   Correct the one document that states the clearing form if the form changes. *Done when:* a
   test runs `set-list --values ""` through the generated executor and reads an empty list back;
   a test pins whatever stripping remains, with the case it exists for.

10. **The step document that regenerates the worktree executor describes what is there.** The
    plugin-doctor finalize step says the worktree's executor is a symlink to main's and tells the
    step to replace it by a generation call with no working directory stated — the call
    deliverable 7 now refuses when issued from the wrong place. State that the worktree executor
    is a generated file, and give the call in the form that writes into the worktree. This
    document is being rewritten by PLAN-LB-32; do this deliverable last, on top of that landing.
    *Done when:* a doc-contract test asserts the step no longer mentions a symlink and that its
    generation call names the worktree as the place it runs.

## Claim Labels

- OBSERVED: the resolver maps two path shapes only — `marketplace/bundles/{bundle}/…` to segment 2 and `{test|tests}/{dir}/…` to segment 1 — and returns `None` unless the derived name is in `registered_modules` — `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_test_scope_divergence.py` § `_module_for_path` (145-185), `_TEST_ROOTS` (59)
- OBSERVED: `resolve_test_scope` returns exactly `scoped_modules`, `divergence_possible`, `recommended_target` and `unresolved_paths`; any unresolved path sets `divergence_possible`, and `recommended_target` is non-null only for exactly one module with no divergence; its `build_map_globs` parameter is accepted and never read — `_test_scope_divergence.py` (188-268, 255, 258-261)
- OBSERVED: `registered_modules` is the set of bundle names from `find_bundles` over the marketplace root, in both callers — `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/pyproject_build.py` § `_resolve_registered_modules` (151-183), `cmd_resolve_test_scope` (186), and `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` (360-373, 401)
- OBSERVED: the build wrapper accepts any existing directory under `test/` as a `module-tests` target and applies no bundle check — repository-root `build.py` § `get_test_path` (411-423), `require_test_path` (426-436), `cmd_module_tests` (645-670), parser (1001-1021); `--filter` maps to pytest `-k`
- OBSERVED: ten top-level directories under `test/` are not bundle names — `_shared`, `default`, `finalize-step-deploy-target`, `finalize-step-sync-plugin-cache`, `fixtures`, `marketplace`, `sync-antigravity`, `sync-harnesses`, `sync-opencode`, `sync-plugin-cache` — read from the tree
- OBSERVED: only the Python build skill has a `resolve-test-scope` verb; `build-api-reference.md` line 44 marks it absent for Maven, npm and Gradle — `marketplace/bundles/plan-marshall/skills/extension-api/standards/build-api-reference.md:44`
- OBSERVED: the tier is `per_task` only when the command key has a measured duration under the ceiling, else `orchestrator` — `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py` § `_lookup_bash_timeout` (318-376, line 370), `_compute_execution_tier_fields` (379-413, line 401)
- OBSERVED: the command key is the tool name plus the full command-args string, so a sub-directory or `--filter` variant has its own key and starts unmeasured — `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` § `compute_command_key` (1069-1081), `default_command_key_fn` (964-979)
- OBSERVED: `execute-task` invokes the resolver once, in Step 5b, and scopes to `recommended_target` or runs whole-tree; it hands an orchestrator-tier build back — `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md:35`, `:269-275`
- OBSERVED: `phase-5-execute` tells the leaf an orchestrator-tier step "is NOT in the leaf's runnable slice" and to return a yield; neither document tells the step to try a narrower run first, and `phase-5-execute` never names the resolver — `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md:224`
- OBSERVED: every path the generated executor embeds is absolute and resolved, and the generator writes to `get_tracked_config_dir() / 'execute-script.py'`, found by walking up from the working directory — `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` (232-234, 2043, 2062-2063, 2096, 2114-2125, 2324-2328), `marketplace/bundles/plan-marshall/skills/tools-file-ops/scripts/file_ops.py` (1474-1504)
- OBSERVED: two callers pin the working directory to the worktree, and one says why: "without the explicit `cwd` the generator would clobber main's executor… `--marketplace-root` only pins bundle DISCOVERY, not the output location" — `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/prepare_execute.py` § `_generate_worktree_executor` (481-560), `git-workflow.py` § `_run_generate_executor` (956-988)
- OBSERVED: the plugin-doctor step issues the same generation with no working directory stated, and describes the worktree executor as a symlink to main's — `.claude/skills/finalize-step-plugin-doctor/SKILL.md:29`, `:150-155`; the worktree executor is never a symlink — `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/_executor_slot.py:33`, `:53`
- OBSERVED: the bootstrap inserts a pinned directory when it exists, else the newest cache directory, else nothing; the import that follows is unguarded — `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` (123-171, 181)
- OBSERVED: the recovery walks `cache_root/<version>/skills/<skill>/scripts`; on this machine the installed layout has a bundle level between the cache root and the version, so the walk matches nothing — template § `_newest_cache_scripts_dir` (123-155); `~/.claude/plugins/cache/plan-marshall/*/*/skills/manage-logging/scripts` matches, the same pattern with one `*` does not
- OBSERVED: `integrate_into_main` does not regenerate the executor — `marketplace/bundles/plan-marshall/skills/workflow-integration-git/scripts/integrate_into_main.py:26`, `:403`, `:518`
- OBSERVED: the executor drops every empty-string argument — template § `main` (1562-1563: "Strip empty string args (defensive: agents may pass empty args from shell variable expansion)"); the clearing form is documented as `--values ""` — `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md:226`; no test covers the strip
- HYPOTHESIS: the cost is as reported — on plan `plan-lb-29-harness-sync`, 11 of 17 execute dispatches ended `voluntary_checkpoint` at 3,937,800 tokens; on `lb-23-verify-builds`, 5 of 7, with three test failures found only at batch runs; directory-scoped runs of the same tests took 15 to 32 seconds. Reported by the two plans' retrospectives, not measured here — confirm/refute on this plan's own execute phase, which is the first to run the changed resolver (verify-at-outline)
- HYPOTHESIS: main's executor was overwritten by the plugin-doctor step's generation call running with the main checkout as working directory — the mechanism is read from the code above; what actually wrote it on 2026-10-09 was not established (the standalone self-review run reported that a test run regenerated it) — confirm/refute by reproducing on a throwaway checkout: generate with `--marketplace-root {worktree}` from the main checkout and compare main's executor before and after (verify-at-outline)
- HYPOTHESIS: a test run can regenerate the working checkout's executor — confirm/refute at `test/conftest.py` § `_ensure_executor_present`; if it can, deliverable 7's refusal must hold for that path too (verify-at-outline)
- HYPOTHESIS: `architecture resolve` accepts a sub-directory as the module argument of `module-tests` — module commands are discovered per module (`_pyproject_cmd_discover.py:571`), so a sub-directory may have no discovered command at all — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` § the resolve handler; if it does not, deliverable 4 includes making it resolvable (verify-at-outline)
- Verify-first clause: settle deliverable 2's mapping source before any code. PLAN-LB-29 (`35b5589b5`) added a project mapping list for the Q-gate module-mapping check (`doc/developer/test-impl-mapping.adoc`, read by `plan-marshall/workflow/q-gate-validation.md`). If that list already states which test tree covers `marketplace/targets/`, the resolver reads it and no second mapping is written; if it is prose for an agent and not machine-readable, decide where the one machine-readable mapping lives and make the document point at it.
- Verify-first clause: before deliverable 1, list which directories under `test/` actually hold tests, and decide per directory whether it is a target or shared infrastructure (`_shared` and `fixtures` are the candidates for the second). Check that a registered non-bundle target does not reach `get_bundle_path` in `build.py`, which exits on a non-bundle name for `quality-gate` and `verify`.
- Verify-first clause: for deliverable 4, read how the learned duration is stored and adapted (`run_config timeout`, the adaptive bound) before choosing the default for an unmeasured single directory, and confirm with the operator if the chosen default exceeds two minutes. Do not lower any existing measured bound.
- Verify-first clause: for deliverable 6, enumerate every reader of `resolve_test_scope` and of `_resolve_registered_modules`, including the docstring mirrors in `_freshness_crosscheck.py` and `phase-6-finalize/scripts/derive_gate_bundles.py`, and record for each whether a wider registered set changes its answer. PLAN-LB-23 (`c9738952a`) rewrote the freshness check; read it as it is now.
- Verify-first clause: for deliverable 9, find out what the empty-argument strip protects against before narrowing it — search the workflow documents for calls that interpolate a possibly-empty value as a bare positional — and keep exactly that case.
- Verify-first clause: deliverable 7 must not break the fallback that copies main's executor into a worktree (`prepare_execute.py` § `_copy_main_executor`), nor the on-main regeneration at the end of finalize (`.claude/skills/finalize-step-sync-plugin-cache/SKILL.md:194-207`), which runs with main as both root and working directory.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_test_scope_divergence.py` — registered targets, source mapping, narrow units (D1, D2, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/pyproject_build.py` — `_resolve_registered_modules`, the `resolve-test-scope` output (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-pyproject/SKILL.md` — verb reference (D1, D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py` — tier for an unmeasured narrow target (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/execute-task/SKILL.md` — Step 5b (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` — the orchestrator-tier yield paragraph only (D5)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/scripts/generate_executor.py` — the cross-checkout refusal, the cache recovery roots (D7, D8)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template` — bootstrap recovery, the argument strip (D8, D9)
- OBSERVED: `test/plan-marshall/build-pyproject/test_test_scope_divergence.py` — resolver cases (D1, D2, D3)
- OBSERVED: `test/plan-marshall/build-pyproject/test_pyproject_build.py` — verb output (D1, D3)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_generate_executor_bootstrap.py` — refusal and recovery (D7, D8)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_generate_executor_template_bootstrap.py` — cache layout walk (D8)
- OBSERVED: `test/plan-marshall/tools-script-executor/test_execute_script.py` — empty argument value (D9)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — only if the shared derivation of registered targets has to move (D6) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` — only if a sub-directory target is not resolvable today (D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/canonical_verify.md` — only if it restates the tier rule for a step (D5) (verify-at-outline)
- HYPOTHESIS: `build.py` — only if a non-bundle target must be told apart from a bundle for `quality-gate` and `verify` (D1) (verify-at-outline)
- HYPOTHESIS: `doc/developer/test-impl-mapping.adoc` — only if the mapping moves or the document must point at it (D2) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-references/SKILL.md` — the clearing form, only if it changes (D9) (verify-at-outline)
- HYPOTHESIS: `.claude/skills/finalize-step-plugin-doctor/SKILL.md` — Step 4 and the symlink sentence, after PLAN-LB-32 has landed (D10) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-architecture/test_cmd_resolve_narrow_target.py` — new tests for the unmeasured narrow target (D4) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/execute-task/test_narrow_unit_doc_contract.py` — new doc-contract tests (D5) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness_narrow_unit_control.py` — the new freshness control (D6) (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/tools-script-executor/test_generate_executor_cross_checkout.py` — new tests for the refusal (D7) (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none for deliverables 1 to 9. Deliverable 10 waits for PLAN-LB-32, which is rewriting the same step document.
- Priority: high. Until deliverables 1 to 5 land, every plan whose changes fall outside a bundle, or inside the largest bundle, pays the hand-back cost on most execute dispatches.
- Suggested order inside the plan: 1 to 3 (the resolver), then 4, then 5 and 6; 7 to 9 are independent of those and of each other; 10 last.
- Overlaps with: PLAN-LB-26 and PLAN-LB-27 on `phase-5-execute/SKILL.md` (this plan edits the orchestrator-tier yield paragraph only); PLAN-LB-32 on `.claude/skills/finalize-step-plugin-doctor/SKILL.md` (deliverable 10 only); PLAN-LB-28 on `manage-architecture/scripts/_cmd_client_handlers.py`, and only if a sub-directory target is not resolvable today.
- Adjacent to: PLAN-LB-26, whose deliverables 4 to 6 change what happens after an orchestrator-tier build reports and how it is waited for. This plan reduces how often a step reaches that hand-back; it does not change the hand-back itself.
- Left out on purpose: a test-scope verb for Maven, npm and Gradle (PLAN-LB-28 owns the Maven test command; the other two have no report yet); making the largest bundle's module-wide test run shorter; per-test time budgets; the outline's domain narrowing that can empty `references.domains` (the executor half of that defect is deliverable 9, the outline half stays an Open Defect); moving the executor's embedded paths from absolute to relative.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-33-leaf-test-scope-and-executor.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
