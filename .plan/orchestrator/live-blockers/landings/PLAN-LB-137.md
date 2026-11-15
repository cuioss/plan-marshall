# Landing Analysis: PLAN-LB-137 — a base-sha evidence recipe, bootstrap containment and the thread-reply flag

epic: live-blockers
workstream: WS-04
pr: #1963 (merge commit `a309ce080610d896a2f96c95abc5a3be445ef936`, one parent `152c913532f2b4fb8eed506f4d55d0470bfbdd92`), and its operator-directed follow-up #1969 (merge commit `862d6205268dfb42fef5904a58bdffd5c9743f45`, one parent `7ac64124b2340dd7b736637b2633d5756d47b77e`)

> Landing record for one shipped plan. Written by the `analyze` verb after verifying claims against ground truth (actual code, artifacts, PR state) — a pasted claim is a lead, never a fact.

## Deliverable Fidelity vs Spec

One message from the runbook lane (sender `rb-lb-137-base-sha-recipe-and-bootstrap-isolation`, `merge_state=merged`, `deliverables 3/3`). It is `complete: false` on `total_tokens` alone (out of scope). The branch was cut at `280e6c404` and merged behind PLAN-LB-139 (`152c91353`), so the squash parent already holds that plan; the diff read is `152c91353..a309ce080` — 26 files, 1184 insertions, 94 deletions.

The facts block agrees with ground truth where the provider can show it: `unresolved_review_threads=0` and `review_body_findings_total=26` equal `runbook_lane review-gate --pr-number 1963` (26 ids: `nitpick-1`, `additional-1`…`additional-3`, `inline-1`…`inline-22`). `review_body_findings_handled=26` is **partly re-verified**: the run's progress file carries a `finding:` line for 21 of the 26 ids (`nitpick-1`, `additional-1`…`3`, `inline-1`…`inline-17`); the other five (`inline-18`…`inline-22`, CodeRabbit review 3 at `b93ba6b57`) are recorded only as one aggregate review line ("5 inline + 1 outside-diff; handled in `037cbd2c7` and `50571c453`; 5 threads replied+resolved"). Those five are **not re-verified** one by one — a missing per-finding disposition line is not evidence the landing lied, and the provider shows 0 unresolved threads. `sonar_open_new_issues=n/a`. No false claim found.

| Deliverable (spec) | Verdict | Evidence |
|--------------------|---------|----------|
| D1 — one base-sha evidence recipe (detached base worktree, four disallowed forms, evidence outlives the copy, removal or `cleanup_owed`) | shipped-modified | `runbook-lane/SKILL.md:393-424` (re-read) states the recipe, the four forms, the evidence home, the removal rule and the no-question-before-a-read rule; `worktree-create --detach` added (`git-workflow.py:2548-2572`, re-read); doc tests `test_runbook_lane.py` (leaf: every asserted string absent at `152c91353`). **Modified:** the recipe has three defects of its own — L3-2, L3-3 below |
| D2 — a bootstrap cannot rewrite another checkout's executor; an unversioned executor is named | shipped-as-specified | `test/conftest.py:241-262` strips both env overrides and pins `.plan/local` (leaf); `generate_executor.py:1746` `UNVERSIONED_SENTINEL`, `resolve_generated_version` (leaf); `_registry_parity_signal` names the cause (`orchestrator.py:6195-6204`, re-read); tests `test_generate_executor_bootstrap.py`, `test_orchestrator_restart_check_registry_parity.py`, `test_generate_executor_behavior.py` (leaf). The preflight reader was missed — L3-1 |
| D3 — the lane names `--for thread-reply`; `body_not_prepared` names it | shipped-as-specified | `ci_base.py` `BODY_PREPARE_COMMANDS` over all six kinds, tied to `VALID_BODY_KINDS` by an import-time assert (leaf); `test_body_not_prepared_names_the_prepare_command_for_its_kind` parametrized over every kind (leaf); GitHub and GitLab pins tightened, not loosened (leaf) |

Files no deliverable or Expected Surface line names: the lane says "Surface drift: none". The leaf traced every outside file to a deliverable or a standing constraint (eight source files and the tests that follow them): `_config_defaults.py`, `upgrade.py`, `_plugin_pin_trap.py` and `runtime_info.py` are readers of the unversioned stamp; `plugin_registry.py` is a docstring; `file_ops.py` holds `TRACKED_CONFIG_ENV_OVERRIDES`, the single source of the env list the bootstrap and the executor seam strip; `prepare_execute.py` strips the same variables on the seam `--detach` relies on; `workflow-integration-git/SKILL.md` documents `--detach`. The executor template changed by a comment only (re-read: three comment lines about the sentinel), so it explains no behaviour change. "None" is therefore generous — twelve files sit outside the declared surface — but none is unexplained, and the surface was under-declared rather than the lane drifting. By the same-act rule no spec is corrected: the spec is shipped and its declaration is a record.

### The amended message and the follow-up (read on 2026-11-12)

The lane amended its message (revision 1, 2026-11-12T10:16:59Z): `self-review: budget-exhausted` is now stated in `steps`, and the message reports a follow-up PR #1969 (`fix/lb-137-followup-round-3`, merge `862d6205`, merged on `7ac64124b`), directed by the operator after the lane's third self-review round left four items open. That explains the operator's statement of 2026-11-11 that the plan was still running: the lane was working on the follow-up after #1963 merged. The state now agrees everywhere: `ci pr view --pr-number 1969` reads `merged` with merge commit `862d6205`, the lane's own message says its worktree was removed and its refs pruned, and `git worktree list` (read) shows no `lb-137` worktree left, while the three other lanes' worktrees are present. The first PR of the follow-up, #1966, was closed on a CodeRabbit quota refusal and recreated as #1969 per the quota policy (the lane's account). The lane asked the operator two questions in total; the second was answered in free text ("if there was at least one CodeRabbit review merge, otherwise recreate PR and re-check"), which the lane did not read as a merge authorization (no review existed on that PR) and recreated the PR instead.

The follow-up diff is 4 files (counted from `git diff --name-only 7ac64124b 862d62052`): `orchestrator.py`, `runbook-lane/SKILL.md`, `generate_executor.py` and `test_preflight_staleness_derivation.py`. The review numbers of #1969 read back against the provider: `unresolved_review_threads` 0 and `review_body_findings_total` 3 (`inline-1` to `inline-3`) equal the lane's "0 unresolved, 3/3 handled"; the handled count is **not re-verified**: the progress file carries 21 `finding:` lines, all for #1963, and none for the follow-up's three findings (a missing disposition record is not a difference). The amended message's own numbers for #1963 are unchanged (0, 26, 26) and the progress file's 21 per-finding lines still cover 21 of the 26 ids.

## Three-Layer Analysis

The landing was read on three layers by one read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface), and the orchestrator re-read the points marked as re-read. The reading is **by reading, no build, no test run, no write**.

- **Dispatch:** one read-only leaf per landing — reason: reading merged code is the depth the dispatch rule exists for, and this 26-file landing was drained in the same firing as PLAN-LB-139, whose read must not share its context.
- **Verdict:** layer 1 clean; layer 2 findings (1 minor, 1 info); layer 3 findings (4 minor, 3 info). No major or blocker. The layer-3 defects are reported to the operator in the same turn; none is staged without the operator's word.

Re-read: `generate_executor.py:3895-3944` and the `_version_tuple` definition; `runbook-lane/SKILL.md:388-427`; `git-workflow.py:2545-2584, 2640-2670`; `orchestrator.py:6130-6204`; the template diff; the five sentinel declarations (`grep`, Grep tool unavailable); the absence of any test of `detach_takes_no_branch` (`grep` over `test/` and the bundles); the progress file's `finding:` lines. **Not re-read** (unverified leads, recorded as such): `test/conftest.py:241-262` and the containment logic, `prepare_execute.py:550`, `ci_base.py:191-353` and the tests that pin it, `git-workflow.py:2735` (the fresh-create `base_ref`), the three test files' docstring wording, the `PLAN_MARSHALL_HOME` fixture use, and the executor-regeneration statement in the landing report (the lane message does not state it).

### Layer 1 — Specified

| Finding | Claim | Verdict | Polarity | Evidence (file:line) |
|---------|-------|---------|----------|----------------------|
| L1-1 | A clone under main's `.plan/temp` walks up to main: `get_tracked_config_dir` resolves `PLAN_TRACKED_CONFIG_DIR`, then `PLAN_BASE_DIR`, then the nearest ancestor holding `.plan/local`, which a fresh clone lacks (git-ignored) | checked (leaf) | confirms | `file_ops.py`, `generate_executor.py` `executor_path()` |
| L1-2 | `worktree-remove` refuses in this lane: it finds its path through the plan's status record and a `--detach` tree writes none | checked (leaf) | confirms | `workflow-integration-git/SKILL.md:1101` |
| L1-3 | The spec's "fails at `9cd644892`" is 19 commits behind the branch base `280e6c404`; `generate_executor.py`, `git-workflow.py` and `file_ops.py` are unchanged in that range and `conftest.py` changed only in temp-root teardown, so the D2 Done-whens are consistent with either sha; `runbook-lane/SKILL.md`, `ci_base.py` and `orchestrator.py` did change and were not read, so the base-sha claim for the D1, D3 and parity Done-whens is not settled by reading | checked (leaf; not re-read) | confirms | leaf |
| L1-4 | The D3 premise "the refusal names `prepare-body`" describes the old message; the Done-when asks for `--for thread-reply` in the new one, which is self-consistent | checked (leaf) | confirms | `ci_base.py` |

No finding names a corpus claim of a staged spec of this epic, so no re-grounding verdict is persisted.

**Layer 1 verdict:** clean.

### Layer 2 — Implemented

| Deliverable | Code trace | Test that can fail | Unexplained file / unborne claim | Verdict |
|-------------|------------|--------------------|---------------------------------|---------|
| D1 | `runbook-lane/SKILL.md:393-424`, `git-workflow.py:2548-2572` | the doc tests in `test_runbook_lane.py` (leaf: presence pins, every string absent at the parent) and `TestWorktreeCreateDetached` in `test_git_workflow_worktree_core.py` | none (twelve files outside the declared surface, all explained) | checked |
| D2 | `conftest.py:241-262`, `generate_executor.py:1746`, `orchestrator.py:6195-6204` | `TestBootstrapContainment` (both tests can fail on the unfixed bootstrap, leaf), the unversioned-stamp tests | none | checked |
| D3 | `ci_base.py:191-353` | `test_body_not_prepared_names_the_prepare_command_for_its_kind[...]` over every kind | none | checked |

- **L2-1 (minor):** the `detach_takes_no_branch` refusal (`git-workflow.py:2559-2565`, re-read) has no test: `grep` over `test/` and the bundles finds the string only in the script and in `workflow-integration-git/SKILL.md:1100`. Removing the guard leaves every new test green. `branch_required` and the detach paths are tested (leaf).
- **L2-2 (info):** the doc tests are presence pins; they show the lane text names the recipe, the four forms, the evidence home and `--for thread-reply`, not that the recipe is coherent — which is where L3-2 and L3-3 sit.
- Executor regeneration: the executor checks each flag against its embedded surface, so the recipe's `worktree-create --detach` is refused until the executor is regenerated (leaf). The landing message does not state it; the spec's constraint ("the landing says so") is therefore not met by the message, though the debt is real and is carried by the operator list in the resume anchor.
- The lane's four open residue items are all confirmed against the merged code below, so its `self-review: budget-exhausted` was honest; the leaf found no open item the lane did not name, but did find the further minors L3-4 to L3-7.

**Layer 2 verdict:** findings — 2 (1 minor, 1 info)

### Layer 3 — Correct

| Defect | File:line | Triggering input | Effect | Severity |
|--------|-----------|------------------|--------|----------|
| L3-1 | `generate_executor.py:3919-3928` (re-read), `_version_tuple` at `:2800-2808` (re-read) | `preflight` with an unresolvable installed manifest, an executor stamped `unversioned` (no `_INSTALLED_VERSIONS` map, which is exactly when the sentinel is stamped) and a real `provisioned_version` in `marshal.json` | The guard excludes only `''` and `'unknown'`, so `unversioned` passes as a readable version; `_version_tuple('unversioned')` is `()` and `_version_tuple(marshal) < ()` is False, so `marshal_status` is `fresh` and the warning claims a "readable pair" — the vacuous `fresh` the comment at `:3911-3914` forbids. Before this landing the same input stamped the empty string and read as `unknown`, so this is a fail-closed regression introduced here. Advisory only (`marshal.json` is never mutated) and a narrow trigger, surfaced through `steward check-staleness` | minor |
| L3-2 | `runbook-lane/SKILL.md:410-424` against `:398-399` (re-read) | any use of the recipe: the plan's test is copied into the base tree, where it is untracked (or modified if the path exists at base) | The removal precondition (clean `status --porcelain`, `:420`) and the reuse precondition (`:398`) can then never hold, and `git worktree remove` without force refuses a tree with untracked files. The text never says to delete the copy first, so every use ends `cleanup_owed=true` and a leftover tree can be neither reused nor removed under the text. The spec's either/or still holds and no wrong evidence results. One clause fixes it: delete the copied file after recording the failing output | minor |
| L3-3 | `runbook-lane/SKILL.md:402-407` (re-read) | a fresh `worktree-create --detach` answering `executor_in_worktree: absent` (the consumer-project install shape) | The non-evidence rule is scoped to "a reuse answer", so a fresh create with an absent executor has no rule; the base run's own unfixed bootstrap then regenerates in place, and `:407`'s claim that the bootstrap short-circuits is false for that case. Whether the build seam passes an inherited `PLAN_BASE_DIR` there is not shown | minor |
| L3-4 | `orchestrator.py:6185, 6196` (re-read); test docstrings (leaf, not re-read) | reading the comments | "the generator now stamps `unversioned`" and "the stamp this codebase now writes" describe a change, not current behaviour; the leaf names the same drift in `workflow-integration-git/SKILL.md:1099` ("no longer an argparse requirement"), `test_runbook_lane.py` ~3067 ("Before this rule the lane said only…"), `test_ci_base_primitives.py` ~694 ("The retired message said…") and `test_orchestrator_restart_check_registry_parity.py:265`. Breaks "current state only" | minor |
| L3-5 | `generate_executor.py:1746`, `_config_defaults.py:1606`, `upgrade.py:767`, `orchestrator.py:931`, `_plugin_pin_trap.py:149` (all five re-read by search) | renaming the literal in the generator | `'unversioned'` is declared five times with no shared source; the conftest env list got an equality test, the sentinel did not (no drift test: leaf, not re-read), so a rename would quietly turn the other four readers back into version readers | minor |
| L3-6 | `git-workflow.py:2653-2656` (re-read), `:2548` (re-read) | `worktree-create --plan-id X-base --branch B` while plan X's detached tree exists at `…/X-base` | The non-detach resume branch answers `worktree_exists` and heals the slot with `allow_copy` at its default, so main's executor can be copied into a base-sha tree — the provenance the detach path forbids. The reverse (detach meeting a branch tree) is refused | info |
| L3-7 | `git-workflow.py:2735` (leaf, not re-read) | `worktree-create --detach` with `--base` omitted | A fresh detached create reports `base_ref` as the requested ref (`HEAD`), not the resolved sha; only the `worktree_exists` path reports `head_sha`. The lane recipe always passes `--base`, which limits the impact | info |
| L3-8 | `orchestrator.py:6139-6140` (re-read) | an empty stamp | The lane's residue item 4 ("a generator that could not read one" contradicts `plugin_registry`) is graded down: without a target the arm reads only `MARSHALL_VERSION`, so an empty stamp can only come from a pre-sentinel executor, written by a generator that could not read a version. The text is imprecise ("an older generator"), not wrong | info |

Containment logic read correctly (leaf, not re-read): a `.plan` symlink is refused before `mkdir`, a `.plan/local` symlink resolving outside the checkout is refused, a dangling symlink maps to `ExecutorBootstrapError`, and the generator replaces a symlinked `execute-script.py` through `os.replace` rather than writing through it. No escape found by reading.

**Layer 3 not shown by reading:** whether the tests pass, and whether the build seam passes an inherited `PLAN_BASE_DIR` into the base tree (L3-3). Only a run could show either.

**Layer 3 verdict:** findings — 8 (5 minor, 3 info; L3-8 is the lane's own item graded down)

### The follow-up (PR #1969) read on three layers

A second read-only leaf (`execution-context-level-5`, `orchestrator.analyze` surface) read the follow-up merge `862d6205` against its parent `7ac64124b` and against the residue this analysis had reported on `a309ce080`; its reason is the same (a separate merged change, read without sharing the first leaf's context). The orchestrator re-read the preflight guard and docstring (`generate_executor.py:3912-3950`), the executor-stamp arms (`orchestrator.py:6130-6205`), the recipe (`runbook-lane/SKILL.md:386-461`), the sender and tree-name derivations (`runbook_lane.py:2942`, `git-workflow.py:2548`) and the whole follow-up diff. **Not re-read:** the two new tests (the leaf reasons through the old guard that both fail on it), `_version_tuple`, `.gitignore`, `git-workflow.py:2639,2706`, `guard.js`, `test_runbook_lane.py:3064-3113` and every conformance row. The leaf reports no rule break of its own.

| Item | Closed? | Evidence |
|------|---------|----------|
| L3-1 preflight reads `unversioned` as readable | **closed**, tested on both pair sides | `generate_executor.py:3921-3928` (re-read): `executor_readable` and `marshal_readable` both exclude `UNVERSIONED_SENTINEL`, so an `unversioned` side gives `unknown`; two new tests (`test_preflight_staleness_derivation.py:65-93`, leaf: both fail on the old guard, because `(0,1,1953) < ()` is False and `() < (0,1,1953)` is True) |
| L3-2 recipe copy makes its own removal precondition unsatisfiable | **closed in the text only** | `SKILL.md:415-420` (re-read): the tree is returned to its tracked state before the check; no test pins it (L2-F1); the deletion step has no Claude file tool (L3-F3) |
| L3-3 fresh create with an absent executor | **closed in the text only** | `SKILL.md:402-405` (re-read): "a creation or reuse answer whose `executor_in_worktree` is `absent` is not evidence"; no test pins it |
| L3-8 / residue 4: an empty stamp attributed to the current generator | **partly closed** | `orchestrator.py:6140` (re-read) names a pre-sentinel executor; the arm at `:6182-6194` (re-read) still says "was generated without a readable version" and "regenerate the executor so it stamps unversioned": one module now gives two causes (L3-F2) |
| L3-4 comment wording describing a change (`orchestrator.py:6185,6196`) | open, as expected | `:6185` "the generator now stamps" and `:6196` "the stamp this codebase now writes" unchanged (re-read) |
| L3-5 sentinel declared five times, no drift test | open, accepted by design in the lane's report (which counts three constants) | `generate_executor.py:1746`, `_config_defaults.py:1606`, `upgrade.py:767`, `orchestrator.py:931`, `_plugin_pin_trap.py:149` |
| L2-1, L3-6, L3-7 (`detach_takes_no_branch` untested; the non-detach resume arm can copy main's executor into a base tree; a fresh detached create reports the requested ref) | open, as expected | `git-workflow.py:2559-2565,2656,2733` (leaf) |

New findings of the follow-up (none major; all in the lane recipe, the preflight guard and one comment):

- **L2-F1 (minor):** the diff changes no runbook-lane test, so none of the new recipe clauses (return to tracked state before the check, the creation-or-reuse absent rule, the owner marker) is pinned; the two doc tests the lane cites assert only older strings (leaf read of `test_runbook_lane.py:3064-3113`). The lane's PR body presents them as the evidence for the lane-text change; whether they pass was not run.
- **L3-F1 (minor): the owner marker serialises nothing.** The recipe says to write `{sender_id}` to `{plan}-base/.plan/local/base-evidence-owner` and to treat a reuse that finds ANOTHER sender in it as a blocker (`SKILL.md:421-424`, re-read). The sender id is `rb-{plan_id}` (`runbook_lane.py:2942`, re-read) and the tree is `{plan_id}-base` (`git-workflow.py:2548`, re-read), so a marker in that tree can only ever hold this plan's own id and "another sender" cannot appear. Two sessions of the same plan both match, neither blocks, and one can remove the other's test copy mid-run; the check-then-write has no atomic step, and the text says nothing about a stale, empty or absent marker (a stale marker is silently reused). The marker and its `.plan/` write exception (`:455`) are also scope no residue item asked for, and the PR body does not mention them.
- **L3-F2 (minor):** the empty-stamp arm of the parity signal still names the old cause (see the table).
- **L3-F3 (minor, the leaf's reading of the guard, not re-read):** "delete the copy using file tools only" (`SKILL.md:415-418`, re-read) has no tool on Claude (Read, Write and Edit cannot delete, `manage-files remove` is plan-scoped), and on OpenCode the guard blocks `rm`; the lane then improvises or leaves the copy, so `status` stays dirty and `cleanup_owed=true`, the failure the follow-up set out to fix. The leaf also notes the original of a tracked file can be read with `git -C {worktree_path} show {base_sha}:{path}`, so the "save under `.plan/temp/`" step (whose `.plan/temp/` is not said, and which is never deleted) is not needed; and that restoring through Read and Write can change trailing newlines or the file mode.
- **L3-F4 (minor, re-read):** the recipe orders the reuse rule ("remove it first when either differs", `:398-399`) before the owner check (`:421-424`), so a second session that finds a tree dirtied by an active first session is told to remove it, not to block; and "Delete the owner marker too before the check. Anything left behind keeps `status --porcelain` dirty" (`:418-420`) contradicts "inside the boundary, so it never dirties the tree" (`:422-423`).
- **L3-F5 (minor, leaf):** the readable test in `cmd_preflight` is a deny-list (`''`, `'unknown'`, the sentinel); any other unparseable stamp (for example `dev`) is still read as a version, `_version_tuple` gives `()` and the vacuous `fresh` or a false `stale` returns. Checking `_version_tuple(v) != ()` would close the class.
- **L3-F6 (info, leaf):** "never dirties the tree" holds only where the BASE sha's `.gitignore` ignores `.plan/*`; this repository's does at the merged commit (`.gitignore:45`) and a consumer project's may not. The follow-up's added comment "`marshal.json` can carry the legacy stamp too" (`generate_executor.py:3925`, re-read) describes a historical state; the test module's docstring (`:5-8`) still says only a missing side reports `unknown`.

**Follow-up verdict:** layer 1 clean; layer 2 findings — 1 minor; layer 3 findings — 6 (5 minor, 1 info) plus the open residue above. Of the original residue, three items are closed (one with tests, two in the text only), one is partly closed and the rest are open.

### Conformance to the Project's Own Rules

| Rule source | Rule | Verdict | Evidence |
|-------------|------|---------|----------|
| CLAUDE.md § Documentation Standards | current state only / no version history | deviates | L3-4: `orchestrator.py:6185, 6196` (re-read) and the docstrings the leaf names |
| CLAUDE.md § Documentation Standards | no timestamps | conforms | leaf: no dates added; PLAN-LB-137 appears as a traceability label in test section headers |
| CLAUDE.md § Documentation Standards | no duplication | deviates | L3-5: the sentinel is declared in five modules with no shared source and no drift test (re-read) |
| CLAUDE.md § Script Execution Convention | scripts only through the executor | conforms | the recipe uses `python3 .plan/execute-script.py … worktree-create --detach`; the raw `git worktree remove` is the spec-sanctioned exception (`:420`, re-read) |
| CLAUDE.md § Workflow Discipline | one command per Bash call | conforms | every command the new lane text prescribes is one invocation (leaf) |
| spec standing constraint | a bootstrap or generator never writes outside its checkout; a refusal is a named reason | conforms | `conftest.py:241-262`, `prepare_execute.py:550`; `branch_required`, `detach_takes_no_branch` (re-read), `worktree_target_conflict`, `plan_local_failed`, `body_not_prepared` (leaf, not re-read) |
| spec standing constraint | tests state their purpose | deviates | leaf: three detach tests have no docstring (not re-read) |
| spec standing constraint | tests use the `PLAN_MARSHALL_HOME` fixture | not_shown_by_reading | `TestBootstrapContainment` sets it by `monkeypatch.setenv`; the detach tests rely on the autouse sandbox |
| spec standing constraint | executor regeneration owed when D1 adds a verb flag, and the landing says so | deviates | owed in fact (leaf); the landing message does not say so (re-read of the message) |

## Metrics and Anomalies

- Tokens: `unknown` (the lane measured none; out of scope). The message names `deepseek-v4.1-flash/high` on the OpenCode harness.
- Duration: not recorded in the message.
- Anomalies: about 42 build submissions, every one `daemon_longpoll`, zero in-process fallback, zero launch-fault retries, zero killed jobs; one `verify` bound expiry (`timeout_used_seconds=1242`) continued with the split form, both parts green; three self-review sub-agents, all completed. Guard: two refusals in the lane's session (`R7` edit in the main checkout, `R5` an `execute-tool` typo), each reissued correctly; one run-own break, a shell `tail` on a build log, recorded in the progress file and reread with the read tool. One amended commit corrected a mistyped trailer before it was pushed (the final trailer is the required one).

## Routing and Merge Behavior

- Review: `coderabbit` (required) reviewed three times, at `58d1039fb` (11 facets), `3146cfee4` (6 inline + 1 outside-diff) and `b93ba6b57` (5 inline + 1 outside-diff), each handled by a fix commit with every thread replied to and resolved; its included allowance was spent by `50571c453`, where it answered `NEUTRAL`/skipping, and the merge went on 0 unresolved threads under the standing rule. `sourcery` (optional) was refused twice on quota (about a 7h24m retry window), recorded, never awaited. The three review numbers read back against the provider: threads 0 and findings total 26 equal the landing; handled 26 is partly re-verified (21 of 26 per-finding lines, the other five aggregate-only) — see Deliverable Fidelity.
- CI/merge: `verify` green on `b93ba6b57` and on `50571c453`; merged through the queue as a squash on `152c91353`, no conflict reported. `cleanup_owed=false`: the lane reports no base tree left behind (not independently checked against the worktree list).
- Sonar: `n/a` — the project has no Sonar.
- Parallelization: no collision with the other three in-flight plans reported. PLAN-LB-146 (build result names the tree built) is staged on the executor template and on `manage-tasks/SKILL.md`; this plan changed the template by a comment only, so nothing there is invalidated, but PLAN-LB-146's outline should read the template at `a309ce080`.

## Reconciliation Actions

The operator said on 2026-11-11 that PLAN-LB-137 was still running, although `ci pr view --pr-number 1963` read `state: merged` with merge commit `a309ce080` and the lane's message read `merge_state=merged`; the status transition was held and the row stayed `running`. On 2026-11-12 the lane amended its message and reported its operator-directed follow-up #1969 merged (`862d6205`) with its worktree removed; `ci pr view --pr-number 1969` reads `merged` and `git worktree list` shows no `lb-137` worktree. The held reading is therefore explained and no longer in conflict with the ledger, and the row is reconciled below. The operator did not state the lane finished in words; the grounds are the lane's own final message and the three provider and git reads above.

- [x] row `status` → `shipped` — `orchestrator queue --transition PLAN-LB-137 --status shipped`
- [x] row `pr` stamped — `orchestrator queue --set-row PLAN-LB-137 --field pr --value 1963` (already stamped on 2026-11-11; the follow-up PR #1969 is named in this report)
- [x] row `landing` stamped — `orchestrator queue --set-row PLAN-LB-137 --field landing --value landings/PLAN-LB-137.md`
- [x] row `plan_marshall_plan_id` stamped — `rb-lb-137-base-sha-recipe-and-bootstrap-isolation` (from the `rb-` sender; already stamped on 2026-11-11)
- [x] epic.md narrative reconciled (queue annotation, decision)
- [x] inbox message `rb-lb-137-base-sha-recipe-and-bootstrap-isolation-001.md` (revision 1) archived
- [x] resume anchor updated and `queue-view.md` regenerated

## Follow-Ups

- Open residue after the follow-up, all of one surface (the lane recipe, the executor sentinel and `worktree-create --detach`), all minor or info, none blocks: the empty-stamp arm still naming the old cause (L3-F2), comment wording that describes a change (L3-4, `orchestrator.py:6185,6196`), five sentinel declarations with no drift test (L3-5), the untested `detach_takes_no_branch` refusal (L2-1), the two info items L3-6 and L3-7, and the follow-up's own findings: the unpinned recipe clauses (L2-F1), the inert owner marker (L3-F1), the deletion step with no tool (L3-F3), the recipe's step order and its contradiction about the marker (L3-F4), the deny-list readable test (L3-F5) and the ignore-file assumption (L3-F6). Carried as one Watch in `epic.md`; a fix plan is staged only on the operator's word, and by the operator rule of 2026-11-11 it would be one plan for this surface, not one per defect. PLAN-LB-146 is running with its own `-base` tree under this recipe, so the recipe's text defects (L3-F1, L3-F3, L3-F4) are live in that lane now.
- Executor regeneration via `/marshall-steward` was already owed; this landing adds that the recipe's `--detach` is refused by a stale executor until it is done.
