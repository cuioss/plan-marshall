envelope_version=1
sender_type=plan
sender_id=rb-lb-97-flat-install-skill-resolution
epic=live-blockers
kind=landing
created=2026-10-27T11:17:37Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-97-flat-install-skill-resolution
epic=live-blockers
pr=#1872
merge_state=merged
cleanup_owed=false
deliverables_total=4
deliverables_done=4
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.2019
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=unknown
step.sonar-roundtrip.open_issue_rules=unknown
```

guard: present

## Deliverables

**D1 — step docs, build extensions and the generator resolve through one flat-aware helper. Fully met.**

| Done-when clause | Verdict | Order | Test | Failing run |
|---|---|---|---|---|
| `resolve_step_doc_path` returns an existing file for `plan-marshall:automatic-review`, `automatic-review`, `default:push` (standards-resident), `default:sonar-roundtrip` | met | `mutation-after` | `test_every_named_step_doc_resolves_on_a_flat_tree` | flat leg removed from `resolve_sibling_skill_path` at `d1c51a39d`: red, resolving `…/skills/automatic-review/SKILL.md` (absent). marshalld job-log `c8201bd1eaed41ff80a3a8266ebf92bb` |
| `get_build_extension_paths` returns the four build skills' `extension.py`, in order | met | `mutation-after` | `test_the_build_extensions_resolve_on_a_flat_tree` | same mutation, same run (`c8201bd1…`) |
| `determine_mode`'s generator path exists in the fixture | met | `mutation-after` | `test_every_generator_path_resolves` (reads the deployed `_generate_executor_script()`) | same mutation: red on `…/skills/tools-script-executor/scripts/generate_executor.py`. job-log `ce6e1785c98a485a865409ea439d65ca` |
| the same assertions in a nested and a versioned-cache fixture return what they returned before | met | `none` (regression clause, no "fails at" wording) | `test_the_nested_source_tree_resolves_what_it_resolved_before`, `test_the_versioned_cache_resolves_inside_the_running_version_dir` | — |

**D2 — a guard keeps every sibling-skill join honest. Fully met.**

- Fails at the base on the D1 joins, passes after — `test-first`. Red on the pre-fix tree (HEAD `90ae7a26e`, whose `marketplace/` and `test/` trees are identical to `a1f981b94`): 17 undeclared sibling joins; `.plan/local/plans/NO_PLAN/build-results/plan-marshall/python-2026-10-26-203652.log`. Note: that run used a pre-commit draft of the guard (line numbers 165/177 vs the committed 245/273) and carried one spurious order-dependent failure; the committed detector is the one that went green, and its content is the same 17-site population.
- Dropping one declaration turns it red — `mutation-after`: dropping `bootstrap_plugin.py`/`tools-file-ops` reds `test_every_sibling_join_is_declared` naming exactly that pair. job-log `0aac43173b4a465ca91aceaf305bcfbb`.
- Adding an undeclared join to a scratch module turns it red — `mutation-after`: `_SCRATCH_JOIN = _SKILLS_DIR / 'automatic-review'` added to `determine_mode.py` reds that test **and** `test_a_routed_module_carries_no_bare_join`. job-log `a91887ab18cd4908a2f0fa8ae4239d34`.

**D3 — the remaining sibling-skill joins are classified and the broken ones fixed. Fully met.**

Every site in the spec's last bullet was read and classified **broken on a flat tree**, then routed: `_ci_log_filter._ensure_build_parser_paths`, `ci_base._load_persist`, `_build_queue_slot._BUILD_QUEUE_PATH` + its dep dirs, `_build_execute_factory._BUILD_SERVER_CLIENT_PATH` + the ledger dir, `integrate_into_main._MERGE_LOCK_PATH`, `git-workflow._GENERATE_EXECUTOR_PATH`, `prepare_execute._GENERATE_EXECUTOR_PATH`. The one site kept declared is `generate_executor.py`'s own `sys.path` bootstrap — which CodeRabbit then proved was *not* flat-safe, and which is now fixed (it derives the flat prefix from its own skill-directory name rather than hard-coding it, probes both shapes, stops at the first existing candidate, and is exercised with an empty `PYTHONPATH`). Order `mutation-after`: job-log `ce6e1785c98a485a865409ea439d65ca` (5 named failures, one per covering test), plus the `PYTHONPATH=''` mutation `b777072266cb48bea236504af04fb0c9` showing `ModuleNotFoundError: argparse_surface`.

**D4 — the upgrade reconcile runs on a flat install. Fully met.**

`sync-defaults --backfill-bot-roster`, `plan phase-6-finalize step get`, `manage-execution-manifest compose`, `validate-loadable --all`, and `_manifest_validation`'s import-time resolution all driven on the flat fixture and compared with the marketplace source checkout. Order `mutation-after`: job-logs `b48c6132f7864454baf290ccd0c72c21` (sync-defaults red with the operator's exact `configurable contract: step body doc not found: …/skills/automatic-review/SKILL.md`) and `bcbf3518a82a4194b5cdad9f686cfa22` (`compose` → `status: error, error: unresolvable_step` while nested returned `success`). The roster the back-fill writes is `required_bots=cuioss-review-bot,coderabbit`, `optional_bots=sourcery` — byte-identical between flat and nested.

Per-head test runs: `verify` (whole tree) green on CI at every head; local `verify plan-marshall`/`verify` green at `395a0d9fb`, `c439fc648`, and the merged head; all four new modules green at each push (`flat` + `sibling_skill_joins` filters).

## Personas and skills

- Production code: `persona-implementer`. Tests: `persona-module-tester`. Every self-review round and every PR-comment triage: `persona-code-reviewer`.
- The spec declares no `Skills:` for any deliverable (`skills_note: none named`), so `skills: none named` per deliverable. No surface drift: every touched file is inside the spec's Expected Surface, plus `tools-script-executor/scripts/generate_executor.py` (reached by D3's own generator clause) and `test/plan-marshall/extension-api/test_extension_discovery_behavior.py` (a seam retarget forced by D1).

## Hypotheses

- **D3 HYPOTHESIS — refuted as stated, split per site.** "The `Path(__file__).parent...` joins … are broken on a flat install, or each has a flat fallback or runs only in a source checkout": every one of the seven sites was broken (silent degradation, not a crash: a missing sys.path entry, a `None` persist layer, a path that does not exist). None had a flat fallback. `marketplace/bundles/plan-marshall/skills/tools-integration-ci/scripts/_ci_log_filter.py:289`, `…/ci_base.py:2134`, `…/script-shared/scripts/build/_build_queue_slot.py:94`, `…/_build_execute_factory.py:173`, `…/workflow-integration-git/scripts/integrate_into_main.py:118`, `…/git-workflow.py:1721`, `…/prepare_execute.py:236`.
- **D4 HYPOTHESIS — confirmed.** Further Stage-2 verbs failed on a flat install for the same cause: `sync-defaults`, `step-get`, and the manifest compose/loadability path (all import-time or step-doc reads through the same joins). No verb failed for a *different* cause, so nothing was left unfixed under D4's last bullet.

## Findings

Self-review round 1 (15 open: 3 blocking, 6 should-fix, 6 nit) — all blocking closed: `determine_mode`'s generator clause got its flat test; the two D2 mutations were recorded; D4 gained `compose`/`validate-loadable` with nested comparison. Fixed: `_scan_phase6_for_implementors` tolerance, three stale docstrings, the guard's blindness to dynamic skill names, the false generator declaration.

Self-review round 2 (10 open: 1 blocking, 5 should-fix, 4 nit) — blocking closed by giving each D1/D3 clause its own test and by seeding the manifest test so `compose` fails on its own surface. Fixed: guard key-collapse (`test_every_declared_join_appears_exactly_once`), D1's miss-reporting at `determine_mode.run_preflight`, `validate-loadable`'s `unloadable_count`, all-candidate probing, the phantom nested flat candidate, the dirty `.plan/marshal.json` (restored by the operator).

Self-review round 3 (6 open: 2 should-fix, 4 nit) — fixed the two cheap nits (single wording for a miss, the "three absent paths" count); the rest are reported as residue below.

CodeRabbit posted 6 findings across three reviews (`89043af24`, `61bc78abc`, `dc57837d4`); all six are fixed (`61bc78abc`, `dc57837d4`, `0407ab40d`) and every thread is replied to and resolved:
1. `_load_parse_log` lost its generic fallback when the deployment root is gone — fixed (`61bc78abc`).
2. `_load_persist` broke its documented "returns None" degradation — fixed (`61bc78abc`).
3. `deployed_skill_md` appended a duplicate top-level `metadata:` — fixed (`61bc78abc`).
4. `ROUTED_MODULES` was a hand-kept roster — derived instead (`61bc78abc`).
5. The generator bootstrap was **not** flat-safe, contrary to its declaration — fixed (`dc57837d4`), mutation-proved.
6. The bootstrap let a flat lib shadow the nested one — fixed (`0407ab40d`).

## Reviewers

- **coderabbit** (required, quota-limited): reviewed `89043af24` (4 findings), `61bc78abc` (1 major), `dc57837d4` (1 minor). Standing review authorization applies to the final head `0407ab40d`: a qualifying review exists on this PR's heads, every finding is handled and every thread resolved, and it was re-triggered after the last push at 10:28 — **refused on its hourly rate limit** ("Review rate limited", next included review in 17 minutes). Every other gate condition held on `0407ab40d`.
- **sourcery** (optional): answered a hard quota refusal at 06:20, then reviewed and APPROVED at `dc57837d4` (later DISMISSED by the next push, which is normal for a dismissed approval). Optional, never gating.

## Operator questions

1. "The executor-skew check answers `could_not_check` … How should I proceed?" — options: Proceed (Recommended) / Regenerate executor first / Stop the run. Selected: **Proceed**.
2. "I mistakenly created four test files in the MAIN checkout … How should they be removed?" — options: You delete them (Recommended) / Grant me deletion permission / Leave them for now. Selected: **Grant me deletion permission** — the grant did not help, because the refusal came from the project's own guard (R2).
3. "The project's own guard (R2) blocks `rm` and `git clean` … Please delete these four untracked files from the MAIN checkout yourself" — options: I deleted them (Recommended) / Leave them until cleanup. Free-text answer: **"give me the git clean command to execute"** → command supplied.
4. "Two files need restoring before the merge … How should they be removed?" — options: Done – both restored (Recommended) / Leave them for the cleanup step. Selected: **Done — both restored**.
5. "PR #1872 is blocked on one merge-gate condition: Sonar … How do you want to proceed?" — options: Keep the PR open (lane default) / Merge anyway, gap accepted / You check the Sonar setup. Selected: **Merge anyway, gap accepted**.

## Rule check

- **Guard.** `guard: present` (OpenCode). The guard refused three of my calls and I did not work around any of them: two `rm` invocations (R2 mutation-class shell file operations) and one `grep … | head` (R1 shell chaining); `git clean -n` was refused by the harness permission layer. Recorded in the operator questions above.
- **`.plan/` state.** Write boundary kept except for one accidental side effect: a D4 test ran before `PLAN_BASE_DIR` was pinned and `sync-defaults` stamped the worktree's tracked `.plan/marshal.json` (`provisioned_version` 0.1.1989 → 0.1.2017). The test now pins the base; the file was restored by the operator rather than by me, because the lane forbids `git checkout --`/`git restore` and the guard blocks shell mutation.
- **Main checkout.** I created the four new test files in the main checkout by mistake instead of the worktree, and could not remove them myself (guard R2). Both the main checkout and the worktree were verified clean before the cleanup steps.
- **Executor.** One bootstrap was run outside the usual path: after a scratch evidence worktree at `a1f981b94` regenerated MAIN's `.plan/execute-script.py` against that (soon deleted) tree, I regenerated it with `generate --marketplace-root .` (opencode target, 334 scripts). The scratch worktree itself was removed with `--force` (it carried its own `.pyprojectx`/`.venv`); the plan worktree was removed without force, as the lane requires. The evidence-worktree route was abandoned because an in-process build always runs in the main checkout and its venv bootstrap diverged; the `mutation-after` evidence replaced it.
- **Build.** Routed builds ran with the daemon throughout (72 module-test/verify invocations observed `mechanism=daemon_longpoll`, no degradation). `--project-dir` must be ABSOLUTE: a relative path resolved against the daemon's cwd and fell back to a system `pwx` that is not installed.
- **Spec read.** `spec_source: main_checkout`; no `spec_differ` marker (the ledger flag was not used, so there was no second copy to compare).

## Build server

Preflight at setup: **ready**; the worktree carried its own executor (`executor_in_worktree: present`) and every routed build submitted with no execution flag. No build degraded, none was killed, no bound expired except one `running` re-attach (verify exceeded the client's 300 s first wait and was re-attached with `build_server wait`, which is the sanctioned bounded re-attach). Two local full-suite runs at the merged head failed only `test/test_harness_shape_guards.py`'s two tree-parsing predicates on their 300 s pytest-timeout under xdist load; both pass in isolation (37/37) and the same suite is green on CI at every head. `runtime_stamp_reason`: not reported.

## Residue

1. **D1's "naming both shapes" holds only where the lookup is fail-loud.** `configurable_contract` and `determine_mode.run_preflight` name both shapes; the never-raising callers (`_manifest_validation`, `extension_discovery`, `prepare_execute`) still report only the nested path on a genuine miss. The Done-when does not require it; reported, not fixed.
2. **The D4 roster is not itself evidence of the doc read.** `required_bots`/`optional_bots` come from `_config_defaults.STANDARD_*` constants, not from `automatic-review/SKILL.md` (whose declared defaults are empty). The doc read is proven by `sync-defaults` succeeding and by `step-get`'s params matching; the roster assertion alone would not catch a broken doc read.
3. **Sonar never became decidable.** Eight reads across five heads answered `undecidable` / `analysis_revision_unavailable` (no analysis revision reported for the PR; `head_revision` resolved to `origin/main`). The operator selected "Merge anyway, gap accepted"; the open new-code count on the merged head is unknown, not zero.
4. **The guard still cannot see every shape.** A `for` over a function parameter, an f-string-composed name, and `os.path.join` are invisible to the bounded AST scan; the non-vacuity test plants the shapes it does cover.
5. **Nits declined:** `_BUNDLE` lives only in `configurable_contract` (ten sites inline the literal); the flat-candidate construction lives in both `flat_skill_paths` and the generator's own bootstrap; the flat fixture hand-assembles source frontmatter plus the identity block rather than running an emitter.
