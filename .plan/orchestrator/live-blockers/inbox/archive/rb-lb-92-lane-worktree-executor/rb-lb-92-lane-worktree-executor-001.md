envelope_version=1
sender_type=plan
sender_id=rb-lb-92-lane-worktree-executor
epic=live-blockers
kind=landing
created=2026-10-24T00:13:36Z

```landing-facts
schema=landing-facts/1
plan_id=rb-lb-92-lane-worktree-executor
epic=live-blockers
pr=#1850
merge_state=merged
cleanup_owed=false
deliverables_total=3
deliverables_done=2
total_tokens=unknown
harness=opencode
model=deepseek-v4.1-flash/high
effort=high
plugin_version=0.1
executor_version=0.1.1996
steps=setup:done,implement:done,build-gate:done,self-review:budget-exhausted,pr:done,reviews:done,merge:done
step.sonar-roundtrip.open_issue_count=0
step.sonar-roundtrip.open_issue_rules=none
```

guard: present on this harness; `.plan/temp/guard.log` carries the refusals listed under Rule check.

# PLAN-LB-92 — a runbook-lane worktree now carries its own executor

Merged as `75a66227a8` (PR #1850), branch `fix/lb-92-lane-worktree-executor`, base `main`.

## 1. Deliverables

**D1 — a lane worktree is created with its executor — MET** (order: `test-first`; failing run at `06cc93771`, build log `python-2026-10-23-154409.log`, 3 failed / 1 passed; green at `332ea4506`)

| Done-when | Test | Verdict |
|---|---|---|
| a fixture lane worktree has a non-empty `.plan/execute-script.py` after creation | `test_creation_produces_a_non_empty_executor` | met |
| a fixture where generation fails and main's executor exists gets the copy | `test_creation_copies_the_main_executor_when_generation_fails` (generation left real) | met |
| a fixture where neither is possible reports `absent` with its reason and does not fail the creation | `test_creation_reports_absent_without_failing_the_creation` (both mechanisms real) | met |
| a lifecycle fixture still reaches phase 5 with the move-in executor | `test_phase_five_move_in_still_produces_its_own_executor` | met |
| "At HEAD `worktree-create` produces no executor" (HYPOTHESIS) | — | confirmed on base: the created worktree's `.plan/` held `local`, `marshal.json`, `orchestrator`, `project-architecture` and no executor |
| decision every-plan vs lane flag, recorded with the reason | verb docstring + `workflow-integration-git/SKILL.md` § worktree-create | met (every plan; see §3) |
| `resolve` / setup states `executor_in_worktree` (`present`/`absent` + reason) | `test_resolve_states_the_worktree_executor_state`, `test_resolve_reports_an_absent_worktree_executor_with_its_reason`, `test_resume_heals_an_executor_less_worktree` | met |

**D2 — a verb refreshes the worktree executor — NOT FULLY MET** (order: `test-first`; failing run at `06cc93771`, build log `python-2026-10-23-155530.log`; green at `ae562b691`)

| Done-when | Test | Verdict |
|---|---|---|
| "a fixture worktree whose branch adds a **script** is stale before the verb and resolves the new notation after it" | `test_the_refresh_maps_a_script_the_branch_added` | **not met as written** — see below |
| the lane text names the verb | `test_skill_names_the_worktree_executor_refresh_verb` | met |
| a doc test asserts no lane instruction runs `generate_executor.py` directly | `test_no_lane_instruction_runs_the_generator_by_path` (whole text, `.py` path form) | met |

Why not met: the generated executor resolves an unmapped notation through its own tree-walking legs (the template's leg 0 on OpenCode, legs 3/4 elsewhere), so a script the branch adds resolves **before** any refresh — the "stale before" half of the clause cannot be observed for that shape, on any target, when the worktree carries a vendored marketplace. The surface-staleness case that *does* exist (a subcommand added to an existing script) was attempted and withdrawn as environment-dependent in a synthetic fixture: whether the embedded surface refuses such a call depends on how confidently the derivation probed that script's `--help` at generation time. What the tests do prove: the rebuilt notation map carries the branch's new script, the verb is registered on the parser the executor derives its surface from, and the refresh never falls back to main's older executor. The clause is reported, not reworded.

The deliverable's "a run never needs a direct interpreter call for it" holds for every plan after this one (the verb is then in main's tree at creation). For the plan that *introduces* it, no executor's surface carries it yet; the lane text now names that one bootstrap case explicitly, through the registered generator **notation** run from the worktree — and names a zero-executor worktree as a blocker instead of hunting for the generator's path. This worktree was created before D1 landed, so it carried no executor at all and the verb was never reachable from it; every build in this run ran `in_process`.

**D3 — builds route through the worktree executor — MET** (order: `test-first`; failing run at `06cc93771`, build log `python-2026-10-23-161915.log`; green at `4b404bbed`)

| Done-when | Test | Verdict |
|---|---|---|
| a fixture lane with a present executor submits a routed build and records no `executor_absent_from_worktree` | `test_build_routing_answers_auto_when_the_worktree_has_its_executor` + `test_the_auto_verdict_submits_the_build_through_the_daemon` (matched control: `_route_to_daemon` reached) | met |
| the same fixture without the executor falls back and records the reason | `test_build_routing_answers_in_process_when_the_worktree_has_no_executor` + `test_the_executor_absent_verdict_runs_the_build_in_process` | met |

Per-head test runs on pushed heads: `ae562b691` — `module-tests plan-marshall` 26,954 pass; `quality-gate` and `test-compile` green; CI `verify` green.

## 2. Personas and skills

- D1/D2/D3 production code: `persona-implementer`; tests: `persona-module-tester`; the two `SKILL.md` edits: `persona-documenter`.
- Spec declared no `Skills:` or `Persona:` lines — `skills: none named`.
- No surface drift: every changed file is on the spec's Expected Surface (the new test file sits in the declared `test/plan-marshall/workflow-integration-git/`).

## 3. Hypotheses

1. "The lane's worktree is created through `worktree-create` with the derived lane name as `--plan-id`" — **confirmed**: this run's own setup used exactly that call (`runbook-lane/SKILL.md` §2 step 3; `git-workflow.py` `cmd_worktree_create`).
2. "A generated executor in a lane worktree resolves the plan's own new script verbs, because the generator discovers bundles from `--marketplace-root {worktree}`" — **confirmed for a verb whose surface the refresh rebuilds**, **refuted for a whole added script** on this harness: `resolve_notation` (template `execute-script.py.template:1564-1589`) walks to a live `marketplace/bundles` tree before consulting the embedded map, so an added script resolves without a refresh. Recorded rather than papered over; it is why D2's Done-when is reported not met as written.
3. The D1 decision (every plan vs lane-only flag) — **decided for every plan**: the executor is per-tree derived state every worktree consumer needs, generation is idempotent and non-fatal, and a flag would add a second path a future caller can forget, which is the defect being closed. Recorded in the verb docstring and the skill's worktree-create section; the phase-5 move-in still generates its own copy.

## 4. Findings

- **Self-review round 1** (12 findings): D2's literal clause accepted as not met (F1); reread of `git-workflow`/`runbook-lane` fixed the resume heal, the verdict split (`executor_produced` vs presence), the lane's two executor call sites, both absence reasons documented, two over-claiming comments, the dropped pre-routing assertion, the doc-test scope, and a matched control test for `auto`. All in `40ec7be18`.
- **Self-review round 2**: the refresh verb was unreachable for the plan that introduces it (circular bootstrap) — the lane text now names the bootstrap case; the resume heal materializes `.plan/local` first; the lazy-import comment corrected; `present` documented as not a promise about content; a parser-registration test added. All in `7bb1100c4`.
- **Self-review round 3**: the doc test now scans the whole text for the generator path; the resume heal is guard-claused so it cannot write outside a worktree; a typo. All in `d1cd10299`. Three rounds spent — reported as `budget-exhausted` with D2's clause still open by design.
- **CodeRabbit finding 1** (major): the shared seam was not guarded — a stale recorded path could be re-created by the copy fallback, and a symlinked `.plan/local` could route a write into another tree. Fixed in `92d821a81` (guard inside `produce_worktree_executor`), with three tests.
- **CodeRabbit finding 2** (major): a refresh could report `executor_regenerated: true` after copying main's older executor. Fixed: `allow_copy=False` for the refresh, existing slot untouched on failure.
- **CodeRabbit finding 3** (minor): the resume payload was undocumented. Fixed.
- **CodeRabbit finding 4** (minor): a resume regenerated over a usable slot, and a transient failure could overwrite a rebuilt executor with main's. Fixed: heal only a missing slot, matching `_already_moved_in_response`.
- **CodeRabbit finding 5** (minor): `executor_produced` could be true when the generator exited 0 having written nothing over a pre-existing file. Fixed: success now requires the slot's mtime to have changed.
- **CodeRabbit finding 6** (minor): inherited `GIT_DIR`/`GIT_INDEX_FILE` could redirect the fixture's git commands. Fixed with an autouse scrub fixture.
- **CodeRabbit finding 7** (major): the refresh could not resolve a runbook-lane worktree at all (no status metadata) — the one caller it exists for. Fixed: structural-probe fallback (`8dce379b0`), plus a test.
- **CodeRabbit finding 8** (minor): the documented refresh payload omitted `executor_in_worktree` and used the wrong detail wording. Fixed.
- **CodeRabbit nitpick**: the no-copy tests stubbed the seam, so removing the production guard would not fail them. Fixed: the test now restores the real generator and lets it fail.
- **CI failure 1**: `test-compile` mypy error in the new fixture helper (`no-any-return`) — `quality-gate` does not cover `test/`; fixed in `4ec6ea3a7`.
- **CI failure 2**: the executor fixture depended on the ambient `PYTHONPATH`, so the generated executor's shared-module imports failed in CI. Fixed in `b15c64f09` (every real skill's `scripts/` dir on the fixture's PYTHONPATH).
- **Pre-existing test adjusted**: `test_prepare_execute_execute_core.py` asserted the literal phrase "no file landed"; the freshness rule makes the truthful wording "wrote nothing new", which is what it now asserts — same strength, same behaviour.
- **Environment failure (not the change)**: `test_target_tree_foundational_skill_freshness.py` failed its own concurrent target-tree regeneration in the first full run (eight xdist workers generating `target/` at once); green once the trees exist. Not reproducible as a code defect; recorded.
- **Build bound expiry**: `verify` hit its 726 s bound; `module-tests` then hit it once too; both recorded and re-run under the split form / a raised timeout.

## 5. Reviewers

| Reviewer | Required? | Outcome |
|---|---|---|
| coderabbit | required, quota-limited | **reviewed** — several reviews; the last completed one covers `0b06a7ac` (`final_review_risk_coverage`, `kind=reviewed`). Eight findings, all fixed and every thread resolved (CodeRabbit confirmed each). Re-triggered after every push; from `21:43:15Z` onward it refused with "Review rate limited" (`rate_limited`, class `awaitable_window`), the last trigger after the final push (`23:02Z`) also refused. Standing review authorization applied: qualifying review exists, every finding handled, re-triggered once after the last push with the refusal recorded, every other gate condition green on `ae562b691`. |
| sourcery | optional, quota-limited | **refused** — "used your own review budget of 250,000 diff characters for the last 7 days … in 3 days and 19 hours". Optional, so no gating; recorded. |

## 6. Operator questions

1. "The runbook-lane run is blocked before `resolve`: the executor is 0.1.1989, the lane text it would run is 0.1.1996, and the executor refuses `executor-skew` with `unknown_verb` (its dispatch surface lists only resolve/build-classify/sonar-facts/sonar-gate). The lane's named remedy is to regenerate the executor, which rewrites `.plan/execute-script.py` in the main checkout — a write this lane does not authorise on its own. How do you want to proceed?" — options {Regenerate, then continue (Recommended); Stop as blocked; Stop the run entirely}; **selected "Regenerate, then continue"**.
2. "`executor-skew` answers `could_not_check` (lane text version not derivable from the flat OpenCode install path), which the lane says must be asked rather than assumed. The executor is 0.1.1996 and the installed bundle is 0.1.1996, so no skew is measurable — how do you want to proceed?" — options {Treat as match and continue (Recommended); Stop as blocked; Probe the versioned cache copy first}; **selected "Treat as match and continue"**.

Free text from the operator: the orchestrator notice about the stray draft in the main checkout (recorded below).

## 7. Rule check

Guard: **present** on this harness. Refusals attributable to this run's session tree (`ses_e96abc760ffewMtVoa6i2TT7n7`), read from `.plan/temp/guard.log`:

- `15:15:25Z` R1 — `grep … | head -40`: a chained shell command. **Kept-rule break**: my own, and the command was abandoned for the grep tool.
- `15:43:16Z` R2 — `rm test/…/test_lane_worktree_executor.py`: a shell file mutation, refused. It was an attempt to remove my own stray write (below).
- `20:42:34Z` R1 — `python3 .plan/execute-tool …; python3 .plan/execute-script.py …`: a chained command containing a typo'd first call. **Kept-rule break**: my own; re-issued as one clean call.

The run's own actions, not only the guard's: **one write to the main checkout** — `test/plan-marshall/workflow-integration-git/test_lane_worktree_executor.py` was created there by mistake early in the run (a relative `write` resolved against the session cwd instead of the worktree). It is still there, untracked, stale (`09f820f`); the worktree copy was authoritative and is what merged. I did not copy it back, edit it, or try to delete it again — `rm` and `git clean` are refused, and removing it is a mutation outside the worktree. **The operator removes it after this run.** Every subsequent edit targeted the worktree.

Routed builds: every build in this run ran `in_process` (`mechanism=in_process_fallback`, `executor_absent_from_worktree`) — the worktree had no executor, which is precisely the defect. No `killed` job. No restarts, no killed sub-agents, no re-dispatched steps; the three self-review rounds were deliberate dispatches, not re-runs.

## 8. Build server

Setup preflight: `ready` (registered, daemon reachable). Every build nonetheless ran `in_process` with reason `executor_absent_from_worktree` — the worktree carried no executor, so `build-routing` answered `in_process` before the first build and that never changed (the refresh verb was unreachable from this worktree; see D2). `verify` hit its own 726 s bound once (`timeout`, `explicit`), and `module-tests` once; the split form (`quality-gate` + `test-compile` + `module-tests` at 1800 s) is the run that is green. No `degraded` result, no `killed` job. `runtime_stamp_reason` was not reported at resolve time; the stamp reads `opencode` / `deepseek-v4.1-flash` / `high` / plugin `0.1` / executor `0.1.1996`.

## 9. Residue

- **D2's "a branch adds a script is stale before the verb" clause is not met as written** — reported in §1 and §3, not reworded or narrowed.
- **The plan that introduces a refresh verb still cannot call it**; the lane text names the one bootstrap route (the generator notation from the worktree) and the zero-executor case as a blocker. Every later plan is unaffected.
- **Stray untracked draft in the main checkout** (see §7) — for the operator to remove.
- `runbook_lane.resolve` reads the worktree slot through the literal `.plan/local/worktrees/{plan_id}`, not `get_worktree_root()`; consistent with the `worktree` value it reports, and pre-existing — flagged by the reviewer, accepted as out of scope.
