# PLAN-LB-158: Follow-ups from the PLAN-LB-153 and PLAN-LB-156 landings — stale ledger statements, the package-phase zero-test guard, and a refusal that names its row

epic: live-blockers
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no brief.

## Objective

Three loose ends the last two landings left behind, closed in one plan because the operator asked for a single follow-up:

1. **Stale statements.** After the phase-5 hand-back commit got its own change-ledger row, three statements in two skill documents still describe the old contract (the source of `changed_paths`, the `manage-status` producer row, and the resolver note). Two advisory documentation items from the same landing ride with them.
2. **A false green.** A `module-tests` run whose leading goal is `package` (the reactor root since the root-aggregator change, and a module consuming a reactor test artifact before it) reports green when the run collected nothing, because the zero-test guard lets a leading `package` through. The `test`-phase form of the same canonical is already held to "something executed". Carry the canonical's intent into the executor so the `package` form is held too, without rejecting a plain compile-and-package run (issue #2000).
3. **An unnamed refusal.** The pre-push freshness gate's `worktree_root_unreadable` refusal names no plan, no build row and no field, and its remedy ("re-dispatch the build") only helps once the executor that wrote the null root is regenerated. Name the plan, the row and the field in the message and say what regenerating the executor changes.

## Deliverables

1. The stale statements are corrected, each to the behaviour the merged code has: `manage-change-ledger/SKILL.md` no longer names `git diff-tree` as the only source of a `kind=change` row's `changed_paths` (a merge commit enumerates its first-parent diff), and its `manage-status` producer row names the per-SHA append invocations the `execute_commits_unrecorded` refusal carries beside the `remap` invocation; `workflow-integration-git/SKILL.md` states that the row is written to the target tree's own ledger and no longer calls every non-`merge_lock` path resolution cwd-relative without that exception, and its `commit` verb paragraph names the merge-commit case; the causal sentence in `plan-marshall/workflow/execution.md` § Orchestrator-tier phase-5 verification names the verb as a third row owner; the `_ledger_core.change_record` docstring no longer says the verb is for a `6-finalize` commit alone.
   - Skills: plan-marshall:ref-code-quality, pm-documents:ref-documentation, pm-plugin-development:plugin-architecture
   - Persona: documenter
2. A `module-tests` run that leads with `package` and produces no test summary and no fresh executed-test report is `indeterminate` (`test_run_executed_nothing`), not green; a plain `package`, `quality-gate` or `verify` run with no test summary keeps its current behaviour. The canonical's intent reaches `apply_zero_test_guard` through the `command_key` channel the executor wrapper already receives, not through the argument string. The limit paragraphs in `standards/maven-impl.md` (§ "Test canonicals of a reactor root" and § "Test ladder for reactor test artifacts") and the `_parse_module_entries` docstring in `_maven_cmd_discover.py` are removed or narrowed to the new behaviour.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
3. Tests pin the new guard: the module-tests `package` empty run is `indeterminate`; the same run with a summary or a fresh report stays green; a `package` run that is not the `module-tests` canonical keeps its green; every existing `package`-phase ladder test in `test/plan-marshall/build-maven/test_maven_execute.py` still passes.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester
4. The `worktree_root_unreadable` refusal names the plan, the offending build row (its position in the ledger and its notation) and the field (`worktree_root`) and says that a row written by an executor generated before the writer fix carries the null, so regenerating the executor is part of the remedy. The refusal's reason code and every other refusal route are unchanged.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: implementer
5. Tests cover the named refusal: a row with a present `null` root yields a message carrying the plan id, the row position, the notation and the field name; a row with the key absent (the legacy shape) is still admitted; the other three tree-identity routes keep their messages; and the refusal documentation in `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness" matches the new text.
   - Skills: plan-marshall:ref-code-quality, pm-dev-python:python-core, pm-plugin-development:plugin-architecture
   - Persona: module-tester

## Standing Constraints

- The three clusters share no file; no deliverable edits another's surface. The documentation correction (D1) states what the merged code does and changes no behaviour.
- The guard change (D2) must not change the verdict of a `package` run that is not the `module-tests` canonical, and must not touch the `test`-phase branch.
- The refusal change (D4) must not change which rows are admitted or refused: only the text of the `worktree_root_unreadable` refusal changes.
- No change under `.plan/orchestrator/` other than the plan's own inbox message.
- Scope-bloat note: five deliverables in three independent clusters, kept in one plan on the operator's word; each cluster is independently shippable inside the plan's own PR.

## Claim Labels

- OBSERVED (re-read at HEAD): `apply_zero_test_guard` returns the result unchanged for a leading `package` goal that carries no summary and no fresh report — `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_execute.py` lines 639-640, the `else: return result` arm; the `test`-phase arm at `:630-638` is the one that answers `test_run_executed_nothing`.
- OBSERVED (re-read at HEAD): the executor wrapper `_selector_miss_guard.execute_direct` receives `command_key` and passes only `args` and `project_dir` to `apply_zero_test_guard` — same file, lines 658-680.
- OBSERVED (consumer-side, issue #2000): the issue's own acceptance clauses are the four listed in deliverable 2 and 3.
- HYPOTHESIS: `command_key` for the module-tests canonical carries the name `module-tests` — confirm/refute at `_build_execute_factory.py` `default_command_key_fn` (verify-at-outline).
- OBSERVED (re-read at HEAD): `_STALE_ROOT_UNREADABLE` is a static text naming neither plan nor row nor field — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` lines 292-297; the refusal routes are one ordered registry at `:315-328`; a present `null` or blank root is read as unreadable and an absent key as the legacy shape (`:360-380`).
- HYPOTHESIS: the candidate rows are carried with their ledger position, so the row can be named without a second read — confirm/refute at `_partition_candidates` (`:405` onward) and its callers (verify-at-outline).
- OBSERVED (re-read on `origin/main`): `manage-change-ledger/SKILL.md` names `git diff-tree --no-commit-id --name-only -r {commit_sha}` as the source of `changed_paths` in its Prohibited list and `git diff-tree` in the Integration table's `commit` verb row, and its `manage-status` producer row carries only the `remap` invocation; `workflow-integration-git/SKILL.md` line 178 says `changed_paths` come "from `git diff-tree` on that commit". The merged writer enumerates a merge commit by `git diff --name-only -r -z {sha}^1 {sha}` — `workflow-integration-git/scripts/git-workflow.py` lines 1033-1054.
- OBSERVED (leaf-reported by the PLAN-LB-153 lane, not re-read): the `workflow-integration-git/SKILL.md` resolver note near line 250 says every non-`merge_lock` path resolution is cwd-relative while the row is written to `{worktree}/.plan/work/change-ledger.jsonl`; the causal sentence at `plan-marshall/workflow/execution.md` lines 558-559; the `_ledger_core.change_record` docstring wording.
- Verify-first clause: the outline settles (a) which value of `command_key` identifies the module-tests canonical and whether the reactor root and the per-module ladder both reach it, and (b) the exact wording of the executor-regeneration remedy the project's own documentation already states, so the message repeats that route instead of inventing one.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/SKILL.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-git/SKILL.md`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/plan-marshall/workflow/execution.md` (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-change-ledger/scripts/_ledger_core.py` (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_execute.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/build-maven/scripts/_maven_cmd_discover.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/build-maven/standards/maven-impl.md` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/build-maven/test_maven_execute.py` (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py`
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` (verify-at-outline)
- HYPOTHESIS: `test/plan-marshall/manage-tasks/` (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none (PLAN-LB-153, -156 and -149 are shipped).
- Overlaps with: none staged. Running at staging time: PLAN-LB-154 (conflicting-baseline recovery), -155 (platform-runtime agent lookup), -157 (the branch-cleanup pre-merge guard); none names a file listed above.
- Adjacent to: `PLAN-LB-121`, `-124`, `-146` and `-149` (shipped) touched the Maven ladder and the freshness gate; their behaviour stays untouched apart from the three changes stated here.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-158-follow-ups-ledger-docs-package-guard-root-diagnostic.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates and edits NO file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
