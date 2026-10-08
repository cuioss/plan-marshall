# PLAN-LB-23: Verify builds: a timed-out build stops completely and names its bound, and the push freshness gate credits the pre-push gate's own green builds

epic: live-blockers
workstream: WS-02

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-23-verify-builds.md` and is queued as one row file, `queue/PLAN-LB-23.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Assembled on 2026-10-08 from PLAN-LB-12, PLAN-LB-01, which this spec supersedes in whole or in part.
> Deliverables, claim labels, surface entries and the carried sequencing notes are copied from those
> specs unchanged. Each deliverable is tagged with the spec and number it came from; inside carried
> text, "deliverable 2" or "D2" means that number of the SAME source spec, and a plan id below
> PLAN-LB-22 resolves through the id map at the end of § Dependencies and Sequencing.

## Objective

A finalize of a Python-touching plan fails to get its green build recorded for two independent reasons. A build that hits its time limit kills only the top process, so its workers keep running, the re-run stacks a second suite on the first, and the result names neither the bound nor its source. And when the pre-push gate does run green, `pre-commit-verify-freshness` refuses every one of its rows because no single row performs every required analysis, so the push halts or pays a second full `verify`. This plan makes both timeout paths stop the whole process tree and report the bound truthfully, attributes gate builds to their plan, and credits the union of green rows at the current worktree SHA. The two sources are one plan because both act on the builds the pre-push gate runs and both edit `phase-6-finalize/standards/pre-push-quality-gate.md`.

### Carried from PLAN-LB-12: A timed-out build leaves its workers running, and nothing names the budget that killed it

Make a build that hits its time limit stop completely, and make its result say which limit stopped it. Today
both timeout paths (the marshalld supervisor and the in-process build wrapper) kill only the top process, so
`uv`, pytest and its xdist workers keep running; the documented re-run then stacks a second whole-tree suite
on the first, which is how a 6–13 minute local `verify` outruns its budget when several plans build at once,
leaves no green verify record, and gets the push refused. Two further faults make the outcome unreadable: a
newer test run in the same checkout can delete an older run's still-live pytest temp directory (the older run
then reports a cascade of `FileNotFoundError`s as a test red), and a routed timeout reports its elapsed time
in the field that should hold the bound, with no statement of where the bound came from. Gate builds are also
filed under no plan, so the owning plan cannot find them. Carries forward process-compliance PLAN-25 D1–D3
and the "timeout never reaps the build" finding of truthful-signals PLAN-TRUTH-169.

### Carried from PLAN-LB-01: The push freshness gate accepts the pre-push gate's own green builds

The `pre-push-quality-gate` finalize step runs `quality-gate`, `test-compile` and `module-tests` green on the
settled tree, and its own document says those builds are what satisfy the freshness precondition of the
`default:push` step that follows. They cannot: `pre-commit-verify-freshness` credits only a single ledger row
whose canonical performs every required analysis, so each of the gate's rows is refused as
`canonical_performs_too_few_analyses` and the verdict is `stale: build_scope_narrow`. Every finalize of a
Python-touching plan therefore either pays a second full `verify` (about 40 minutes) or halts at push and asks
for an override that the operator has been told never to give. Make the freshness check credit the union of
green build rows at the current worktree SHA when together they cover every required analysis at an adequate
scope, so the gate's own runs are sufficient. Carries forward truthful-signals PLAN-TRUTH-186 (all
deliverables) and process-compliance PLAN-23 deliverable D3.

## Deliverables

1. **[PLAN-LB-12 D1]** **The daemon stops the whole process tree on timeout.** `run_job` starts the build child in its own
   process group (or session) and, on expiry, signals the group — terminate, a short grace period, then kill —
   instead of the single `proc.kill()`. Done when a new test in
   `test/plan-marshall/build-server/test_marshalld_supervisor.py` runs a child that spawns a grandchild which
   outlives it, lets the supervisor time out, and asserts the grandchild's pid is gone afterwards; the test
   fails at HEAD. The existing `test_run_job_timeout` and the `killed`-vs-`timeout` classification tests stay
   green: a group kill the supervisor sent is still `timeout`, never `killed`.

2. **[PLAN-LB-12 D2]** **The in-process build wrapper stops the whole process tree on timeout.** `execute_direct_base` replaces
   its two `subprocess.run(..., timeout=...)` calls with a launch that owns a process group and kills the
   group on expiry, for both capture strategies. Done when a test in
   `test/plan-marshall/script-shared/test_build_execute.py` shows a timed-out command's grandchild is gone
   and the result is still `status: timeout` with the learner fed exactly as today; fails at HEAD. An external
   signal to the wrapper itself (SIGTERM/SIGINT) takes the group down with it — see the verify-first clause on
   SIGKILL.

3. **[PLAN-LB-12 D3]** **Pruning the pytest temp root never removes a live run's directory.** `_prune_basetemp_roots` treats a
   per-session directory whose owning build process is still alive as not removable, whatever its age, size
   or position in the keep-count; only directories of finished or dead runs count against the two retention
   bounds. Done when a test in `test/default/test_build_verify.py` creates three session directories, marks
   the oldest as owned by a live pid, makes the newer ones large enough to trip `PYTEST_BASETEMP_MAX_ENTRIES`,
   and asserts the live one survives a prune while a dead-owner directory of the same age is removed; fails at
   HEAD. The retained-history bounds still hold for dead sessions (existing tests stay green).

4. **[PLAN-LB-12 D4]** **A timeout or kill result names its bound and the bound's source.** Every `timeout` and `killed` build
   result carries `timeout_used_seconds` = the bound actually applied, plus `timeout_source`
   (`explicit` | `learned` | `default` | `floor` | `daemon_default`) and the `command_key` the learned value
   was read under; the routed leg reports the bound, not the elapsed time. Done when (a) a routed timeout
   whose job ran 300 s under an 1800 s daemon bound renders `timeout_used_seconds: 1800`,
   `timeout_source: daemon_default` (at HEAD it renders the duration), (b) an in-process timeout under a
   learned value renders `timeout_source: learned` with the key, and (c) the three fields survive
   `_build_format` filtering into the printed TOON; tests in `test_build_timeout_truthfulness.py` and
   `test_explicit_timeout_routing.py`.

5. **[PLAN-LB-12 D5]** **Gate builds are attributed to their plan.** The builds the finalize gates run (pre-push quality gate,
   and any other finalize step that runs an architecture-resolved `executable` verbatim) carry the plan's id,
   so the daemon job row, the build log directory and the `[BUILD-SERVER] resolved build` line all name the
   plan instead of `NO_PLAN`. Done when a test resolves a build command for a plan, applies the documented
   gate invocation, and asserts the submitted `plan_id` equals the plan; plus a doc-contract test that no
   shipped finalize standard instructs running a resolved build executable without the plan-id step.

6. **[PLAN-LB-01 D1]** **Union coverage at one SHA.** When no single candidate row covers the change, the coverage dimension
   combines the candidate rows (already restricted to `kind=build`, `status == success`, current
   `worktree_sha`) and reports `covered` when, for EVERY required analysis, at least one row performs that
   analysis at a scope adequate for the change: whole-tree when `RequiredCoverage.whole_tree` is true,
   otherwise a scope containing `RequiredCoverage.modules`. Scope is judged per analysis, never pooled — a
   module-scoped `quality-gate` row does not lend its scope to a whole-tree `module-tests` row or the reverse.
   A row that measured zero tests contributes no `test` coverage; a row whose `args` are unreadable or whose
   canonical is outside the vocabulary contributes nothing. The joint verdict with the attribution dimension
   holds per contributing row: a row the architecture cannot attribute does not contribute. The `fresh`
   record names every contributing row (ledger index, canonical, scope), not one "chosen" row.
   Done when: a test builds a ledger holding green whole-tree `quality-gate`, `test-compile` and
   `module-tests` rows at SHA X with the worktree at X and a `.py` footprint, and
   `pre-commit-verify-freshness` returns `status: fresh` with `scope_cross_check: covered` and all
   contributing rows listed. The same test fails today with `stale` / `build_scope_narrow`.

7. **[PLAN-LB-01 D2]** **A refusal names what is missing.** When the union still falls short, the `stale` record carries the
   uncovered analyses as a field (for example `missing_analyses: [test]`) beside the existing per-row
   `row_scopes`, and the message says which analysis no row covered at an adequate scope. The `reason` token
   stays `build_scope_narrow` unless the outline finds no consumer branching on it; `push.md` and
   `manage-tasks/SKILL.md` both key on it today.
   Done when: a ledger with only green `quality-gate` and `test-compile` rows at the current SHA returns
   `stale` naming `test` as missing; a ledger whose only `quality-gate` rows are module-scoped while the
   change requires whole-tree returns `stale` naming `lint`.

8. **[PLAN-LB-01 D3]** **Documents match the behaviour.** `pre-push-quality-gate.md` § "Settle-band position" (the sentence that
   says only this gate's just-completed builds can have written the admitting row) becomes true as written;
   `push.md` § "Freshness precondition" stops describing freshness as "the most recent `verify` run" and
   describes the union basis, including how the step's `--display-detail` renders a multi-row basis;
   `manage-tasks/SKILL.md` § "Pre-Commit Verify Freshness" documents the union rule in its coverage table
   and its `build_scope_narrow` remedy row (the remedy is "run the missing analysis", not "re-run verify").
   Done when: the three documents state the union rule once (`manage-tasks/SKILL.md` owns it, the other two
   point at it) and the existing document-contract tests for these files pass.

9. **[PLAN-LB-01 D4]** **Controls that keep the gate closed where it must be.** Pinned as tests beside the existing
   `test_pre_commit_verify_freshness*.py` modules: (a) the Deliverable 1 row set at SHA X with the worktree
   at Y returns `stale`; (b) a covering set in which the only `module-tests` row has `status: killed` or
   `timeout` returns `stale` (that row is never a candidate); (c) a covering set whose `module-tests` row
   measured zero tests returns `stale`; (d) a single green whole-tree `verify` row still returns `fresh`
   with the same record shape as before, plus the new contributing-rows field holding that one row; (e) a
   covering set in which one needed row carries a notation the architecture does not resolve returns
   `stale`.

## Claim Labels

Carried in source order: bullets 1 to 24 from PLAN-LB-12; bullets 25 to 41 from PLAN-LB-01.

- OBSERVED: the daemon's timeout path kills one process — `proc = await asyncio.create_subprocess_exec(...)` is created without `start_new_session`/`process_group`, and expiry runs `proc.kill()` then `proc.wait()` — read at `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_supervisor.py:313-332` § `run_job`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _marshalld_supervisor.py run_job :313-332: create_subprocess_exec(*command, cwd, env, stdout, stderr) with no start_new_session/process_group; on TimeoutError proc.kill() then await proc.wait()
- OBSERVED: the daemon child is not the test runner but a chain — `python3 .plan/execute-script.py <notation> run …` re-running the build wrapper, which runs `./pw`, which runs `uv run pytest` with xdist workers — so one `kill()` reaches only the first link; read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:767` § `_route_to_daemon` and `build.py:305-310` § `run`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_execute_factory.py _route_to_daemon :767 builds ['python3', .plan/execute-script.py, notation, *sys.argv[1:]]; build.py run :305-310 is subprocess.run(cmd); cmd_module_tests runs 'uv run pytest ... -n auto'
- OBSERVED: the in-process leg has the same fault — both branches call `subprocess.run(cmd_parts, timeout=timeout_seconds, …)`, whose expiry kills only the direct child — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute.py:259-280` § `execute_direct_base`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_execute.py execute_direct_base :259-280: both capture branches call subprocess.run(cmd_parts, timeout=timeout_seconds, ...); no process-group or session argument
- OBSERVED: no process-group handling exists anywhere on the build path — a search of `script-shared/scripts/build/`, `manage-build-server/scripts/`, `build-server-client/scripts/` and `build.py` for `start_new_session|killpg|setsid|getpgid` finds only the daemon's own daemonization (`marshalld.py:238`, `manage_build_server.py:275`)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: architecture search for start_new_session|killpg|setsid|getpgid|process_group: build-path hits only marshalld.py (os.setsid :238) and manage_build_server.py (start_new_session=True :275); build.py read in full, none
- OBSERVED: every pytest invocation gets its own directory `.plan/temp/pytest-basetemp/{pid}-{uuid4}` and prunes the shared root first — read at `build.py:264-291` § `_prepare_session_basetemp`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: build.py _prepare_session_basetemp :264-291: mkdir root, _prune_basetemp_roots(), then PYTEST_BASETEMP_ROOT / f'{os.getpid()}-{uuid.uuid4().hex}'; called from cmd_module_tests and cmd_coverage
- OBSERVED: the prune protects only the newest directory; any older one is removed when it falls outside `PYTEST_BASETEMP_KEEP = 3` or when the running entry total would pass `PYTEST_BASETEMP_MAX_ENTRIES = 100_000`, with no check that its owner is still running — read at `build.py:190-261` § `_prune_basetemp_roots` (the newest-dir exception and its `popen-gwN` symptom comment are at `:236-249`)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: build.py _prune_basetemp_roots :190-261: KEEP=3, MAX_ENTRIES=100_000; only index==0 is exempt (popen-gwN comment :236-249); session_dirs[retained:] are rmtree'd with no owner-liveness check
- OBSERVED: the source comment sizes one whole-tree session at about 92,000 entries, so two overlapping whole-tree runs in one checkout exceed the 100,000-entry budget and the older, still-running one is the removal candidate — read at `build.py:128-149`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: build.py :128-149 comment: 'three retained sessions of ~92k entries each' and MAX_ENTRIES 'sized to admit roughly one session'; prune breaks at the first dir over budget, so an older dir is removed
- HYPOTHESIS: the pid in the directory name is the `build.py` process, which stays alive for the whole pytest run because `run()` blocks in `subprocess.run`, so `os.kill(pid, 0)` is a sound liveness probe — confirm/refute at `build.py` § `_prepare_session_basetemp` and § `cmd_module_tests`/`cmd_coverage` (verify-at-outline)
- HYPOTHESIS: the overlap that triggers the deletion is two runs in the SAME checkout (the root is a cwd-relative path, so separate worktrees have separate roots), admitted concurrently because the scheduler checks only the global slot — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_scheduler.py` § `admit_next` (verify-at-outline)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _marshalld_scheduler.py admit_next :202-223 gates only on available_slots()==0 (global max_slots) plus round-robin; no per-tree exclusion. build.py PYTEST_BASETEMP_ROOT is the relative Path('.plan/temp/pytest-basetemp')
- OBSERVED: a routed timeout reports its elapsed time as the bound — `timeout_result(duration, duration, log_file, command_str)` passes `duration` as `timeout_used_seconds` — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:631-632` § `_daemon_result_to_direct` and `:696-697` § `_result_for_log_verdict`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_execute_factory.py _daemon_result_to_direct :631-632 and _result_for_log_verdict :696-697 both return timeout_result(duration, duration, log_file, command_str); first positional is timeout_used_seconds
- OBSERVED: the routed `killed` result carries no bound at all (`killed_result(exit_code=…, duration_seconds=…, log_file=…, command=…)`) — read at `_build_execute_factory.py:633-645`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_execute_factory.py :633-645: routed WIRE_STATUS_KILLED arm calls killed_result(exit_code=, duration_seconds=, log_file=, command=) with no timeout_used_seconds; only 'message' is overlaid
- OBSERVED: no result names where a bound came from — `timeout_source` has zero hits under `script-shared/scripts/build/` and `manage-build-server/scripts/`; `timeout_used_seconds` is the only bound field (`_build_result.py:370-400`, `_build_format.py:44`)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: architecture search 'timeout_source': hits only in tools-script-executor SKILL.md and wait-pattern.md, none under script-shared/scripts/build or manage-build-server/scripts; _build_result.py :370-400, _build_format.py :44 carry timeout_used_seconds
- OBSERVED: the applied bound has four possible origins that the result cannot distinguish — explicit `--timeout`, a persisted value times `SAFETY_MARGIN = 1.25`, the tool default, or a floor (`MINIMUM_TIMEOUT_SECONDS = 120`, `min_timeout`) — read at `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py:244-274` § `timeout_get` and `_build_execute.py:237-240`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: run_config.py :25-27 SAFETY_MARGIN=1.25, MINIMUM_TIMEOUT_SECONDS=120; timeout_get :244-274 explicit / persisted*margin / default, floored; _build_execute.py :237-240 max(timeout_get(...), min_timeout)
- OBSERVED: the daemon's own bound is a fifth origin — `_DEFAULT_JOB_TIMEOUT = 1800`, raised to `requested + 30` only when the submit stated a bound — read at `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py:73-91,600-619` § `_resolve_job_timeout`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: marshalld.py _DEFAULT_JOB_TIMEOUT = 1800 (:73), _JOB_TIMEOUT_MARGIN_SECONDS = 30 (:85); _resolve_job_timeout :600-619 returns self._job_timeout when requested is None, else max(requested + 30, self._job_timeout)
- HYPOTHESIS: the recorded "killed at 783 s against a measured 1434 s" was the child's own learned bound (a persisted ~627 s × 1.25) and the 1434 s figure was read after the timeout path doubled the stored value (`timeout_set(command_key, min(timeout_seconds * 2, MAX_TIMEOUT))`), i.e. the two numbers are the same key before and after — confirm/refute at `_build_execute.py:337-342` and `run_config.py:237-241,319-328` (verify-at-outline)
- OBSERVED: an absent `--plan-id` becomes the `NO_PLAN` sentinel for every build-class handler — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_cli.py:692-701` § `build_main`, and is what the daemon is told (`routing_plan_id = plan_id or NO_PLAN_SENTINEL`, `_build_execute_factory.py:773`)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_cli.py build_main :692-701: args.plan_id = args.plan_id or NO_PLAN_SENTINEL; _build_execute_factory.py :773 routing_plan_id = plan_id or NO_PLAN_SENTINEL passed to run_submit and run_wait
- OBSERVED: the pre-push gate resolves each build with `architecture resolve … --audit-plan-id {plan_id}` and then runs "the captured `executable` verbatim"; no step adds `--plan-id` to that executable — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:240-245,257-268,307-314`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: pre-push-quality-gate.md read in full: every build arm is 'architecture resolve ... --audit-plan-id {plan_id}' then 'run the captured executable verbatim'; no step appends --plan-id to a resolved build executable
- OBSERVED: `--audit-plan-id` is consumed by the generated executor for its own log line and stripped before the script runs, so it never reaches the build wrapper — read at `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template:1344-1376` § `extract_audit_plan_id`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: execute-script.py.template extract_audit_plan_id :1344-1376 returns (audit_plan_id, cleaned args without the flag); _args_for_logging :1313 re-injects --plan-id only for the log record ('stripped before dispatch')
- OBSERVED: a helper that inserts `--plan-id` after `run` for build notations exists but belongs to the execute phase — read at `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py:106-169` § `inject_project_dir`
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: execute-task/scripts/inject_project_dir.py inject_project_dir :106-169: for Bucket B notations followed by 'run', inserts ['--plan-id', plan_id] after 'run'; lives in the execute-task skill, called by phase-5
- HYPOTHESIS: `architecture resolve` returns an `executable` with no `--plan-id` even when called for a plan, so attribution can be fixed either in the resolver (emit the flag when a plan id is supplied) or in the gate document (apply the existing helper) — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` § `cmd_resolve` (verify-at-outline)
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_client_handlers.py cmd_resolve :389-432 calls resolve_command(args.resolve_command, args.module, args.project_dir) and never reads a plan id; live resolve of module-tests returned an executable with no --plan-id
- Verify-first clause: decide the kill mechanism before scoping D1/D2. A new session detaches the build from the caller's process group, so a harness that SIGKILLs the wrapper can no longer reach the build through the group; a handler can forward SIGTERM/SIGINT/SIGHUP but not SIGKILL. Settle whether the wrapper uses a new process group with signal forwarding, and state in the result or the log what an un-forwardable kill leaves behind. Do not ship a variant that makes a harness reap leave MORE processes than today.
- Verify-first clause: D1 and D2 are POSIX mechanisms (`os.killpg`). State the Windows behaviour explicitly (unchanged single-process kill is acceptable) rather than leaving it undefined.
- Verify-first clause: D3 must fail safe. An unreadable or unparsable owner pid, or a pid that was reused by an unrelated process, must resolve to "keep", never to "remove"; the cost of a wrong "keep" is one extra retained directory, the cost of a wrong "remove" is a destroyed run.
- Verify-first clause: for D5, enumerate every shipped workflow document that runs a resolved build `executable` (not only the pre-push gate) from a search of `marketplace/bundles/plan-marshall/skills/**/*.md` for the resolve-then-run pattern, and fix the set that search returns; do not assume the gate is the only site.
- OBSERVED: each candidate row is judged alone and must perform every required analysis — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` § `_row_refusal` (:504-539, the test is `if not required.analyses <= performed: return ROW_CANONICAL_TOO_WEAK` at :530-531).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _freshness_crosscheck.py _row_refusal :504-539 judges one entry; :530-531 'if not required.analyses <= performed: return ROW_CANONICAL_TOO_WEAK'
- OBSERVED: no cross-row aggregation exists — `_freshness_crosscheck.py` § `scope_check_candidates` (:548-629) loops `_row_refusal` per row (:595-603), returns `COVERED` only when some single row passed (:605), and otherwise returns `NARROW` / `REASON_SCOPE_NARROW` (:624-628).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _freshness_crosscheck.py scope_check_candidates :548-629: per-row loop over _row_refusal :595-603, COVERED only 'if covered' :605, else NARROW / REASON_SCOPE_NARROW :624-628; no union across rows
- OBSERVED: the refusal tokens are `REASON_SCOPE_NARROW = 'build_scope_narrow'` (:257) and `ROW_CANONICAL_TOO_WEAK = 'canonical_performs_too_few_analyses'` (:272) in the same file.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _freshness_crosscheck.py :257 REASON_SCOPE_NARROW = 'build_scope_narrow'; :272 ROW_CANONICAL_TOO_WEAK = 'canonical_performs_too_few_analyses'
- OBSERVED: a `.py` footprint requires compile, lint and test; any non-empty footprint requires test — `_freshness_crosscheck.py` § `required_coverage` (:375-427).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _freshness_crosscheck.py required_coverage :375-427: analyses = {test} for any non-empty footprint, plus {compile, lint} when any path ends with '.py'; empty footprint requires nothing
- OBSERVED: no gate arm's canonical performs all three analyses — `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_examined.py` § `CANONICAL_ANALYSES` (:97-106) maps `quality-gate` to compile+lint, `test-compile` to compile, `module-tests` to test, and only `verify` to all three.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _build_examined.py CANONICAL_ANALYSES :97-106: quality-gate {compile, lint}, test-compile {compile}, module-tests {test}, verify {compile, lint, test}; only verify carries all three
- OBSERVED: the gate runs those three canonicals and never `verify` — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` §§ "Run quality-gate per bundle", "Whole-tree quality-gate arm", "Whole-tree test-compile gate", "Whole-tree module-tests divergence gate".
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: pre-push-quality-gate.md sections 'Run quality-gate per bundle', 'Whole-tree quality-gate arm', 'Whole-tree test-compile gate', 'Whole-tree module-tests divergence gate' resolve only those three canonicals; none resolves verify
- OBSERVED: the gate document claims its own rows admit the push — `pre-push-quality-gate.md:54` ("it permits on a `kind=build` ledger entry carrying the current worktree SHA, which only this gate's just-completed builds can have written for the settled tree").
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: pre-push-quality-gate.md :54 carries the quoted sentence verbatim ('it permits on a kind=build ledger entry carrying the current worktree SHA, which only this gate's just-completed builds can have written')
- OBSERVED: `push.md:62` describes freshness as verifying "that the most recent `verify` run actually observed this version of the code" — `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md`.
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: push.md :62: 'freshness verifies *that the most recent `verify` run actually observed this version of the code*'
- OBSERVED: candidates are pre-filtered to `kind == build`, `status == 'success'` and the current `worktree_sha` before the cross-check runs, so red, killed and timed-out rows are never candidates — `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` § `cmd_pre_commit_verify_freshness` (the `candidates = [...]` comprehension).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_pre_commit_verify_freshness.py cmd_pre_commit_verify_freshness :611-617: candidates comprehension filters kind == KIND_BUILD, status == 'success', worktree_sha == current_sha before _verdict_for_candidates
- OBSERVED: the `fresh` record cites exactly one row through `_evidence_fields(ledger_indices[chosen], ...)` — `_cmd_pre_commit_verify_freshness.py` § `_verdict_for_candidates` (:458-469); the joint selection is `chosen = admissible[0]` at `_freshness_crosscheck.py` § `cross_check_candidates` (:812-815).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: _cmd_pre_commit_verify_freshness.py :458-469 fresh record spreads _evidence_fields(ledger_indices[chosen], candidates[chosen][1]); _freshness_crosscheck.py :812-815 chosen = admissible[0] if (not refused and admissible) else None
- OBSERVED: the documented coverage contract states the single-row rule — `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md:327-328` (`covered`: "At least one row's canonical performs every required analysis") and `:433` (`build_scope_narrow` remedy).
  - verdict: corroborated | checked_at: 726ca857a | by: live-blockers/cleanup | rescoped: n/a | evidence: manage-tasks/SKILL.md :327 'covered | At least one row's canonical performs every required analysis ...'; :433 build_scope_narrow row with remedy 'Re-run a build whose canonical and scope cover this change'
- HYPOTHESIS: in real finalize runs all four gate arms were green on the exact tree (28,128 and 28,166 tests) and push still refused `build_scope_narrow` with every row `canonical_performs_too_few_analyses` — reported by two plan runs, not reproduced here; confirm by building that row set against `_freshness_crosscheck.py` § `scope_check_candidates` (verify-at-outline).
- HYPOTHESIS: every green arm of one gate pass stamps the same `worktree_sha` as the settled tree — `quality-gate` rewrites tracked files in place (`ruff check --fix`, `ruff format`), so a row stamped before an auto-fix would carry a different SHA than the rows after it and could not join the union; confirm/refute at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/worktree_sha.py` § `compute_worktree_sha` and the build wrapper's ledger-stamping site (when the SHA is computed relative to the build) (verify-at-outline).
- HYPOTHESIS: the per-bundle `quality-gate` rows and the module-scoped `module-tests` row carry their scope as bare tokens after the canonical in `--command-args`, which is what `parse_row_scope` reads — confirm at `_freshness_crosscheck.py` § `parse_row_scope` against a real ledger row written by a module-scoped run (verify-at-outline).
- Verify-first clause: reproduce the refusal from the Deliverable 1 fixture against HEAD before changing anything; if HEAD already admits a union, shrink the plan to Deliverables 2 and 3.
- Verify-first clause: if the `worktree_sha` hypothesis is refuted (an auto-fixing `quality-gate` leaves earlier rows at another SHA), settle at outline whether the gate re-runs the affected arm or the plan stops at "union only when all rows share the SHA" and reports the remaining case; do not widen the union across SHAs.
- Verify-first clause: decide the shape of the multi-row evidence fields once and check every reader of the `fresh` record (`push.md` display-detail basis, phase-5 Step 12a, tests) before changing `_evidence_fields`.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_supervisor.py` — `run_job` process-group launch and group kill (D1), bound source on the terminal payload (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py` — `_resolve_job_timeout` reports which origin it chose (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute.py` — `execute_direct_base` group launch/kill and `timeout_source` (D2, D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — `_daemon_result_to_direct`, `_result_for_log_verdict` report the bound, not the duration (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` — `timeout_result` / `killed_result` fields (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_format.py` — field allow-list for the printed TOON (D4)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — `cmd_run_common` carries the new fields through the timeout and killed renderings (D4)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_server_protocol.py` — wire payload carries the bound and its source from daemon to client (D4) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py` — `timeout_get` returns or exposes which path produced the value (D4) (verify-at-outline)
- OBSERVED: `build.py` — `_prune_basetemp_roots`, `_prepare_session_basetemp` liveness-aware retention (D3)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — the resolve-then-run instructions gain the plan id (D5)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` — `cmd_resolve` emits `--plan-id` in the executable when called for a plan, if the resolver-side remedy is chosen (D5) (verify-at-outline)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py` — reused or relocated as the shared plan-id step, if the document-side remedy is chosen (D5) (verify-at-outline)
- OBSERVED: `test/plan-marshall/build-server/test_marshalld_supervisor.py` — grandchild-reaped test (D1)
- OBSERVED: `test/plan-marshall/build-server/test_explicit_timeout_routing.py` — routed bound and source (D4)
- OBSERVED: `test/plan-marshall/script-shared/test_build_execute.py` — in-process group kill (D2)
- OBSERVED: `test/plan-marshall/script-shared/test_build_timeout_truthfulness.py` — bound/source fields (D4)
- OBSERVED: `test/plan-marshall/script-shared/test_build_format.py` — fields survive formatting (D4)
- OBSERVED: `test/default/test_build_verify.py` — live-owner prune test (D3)
- HYPOTHESIS: `test/plan-marshall/phase-6-finalize/test_gate_build_plan_attribution.py` — new attribution and doc-contract test (D5) (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_freshness_crosscheck.py` — union rule in `scope_check_candidates` / `cross_check_candidates`, missing-analysis reporting
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/scripts/_cmd_pre_commit_verify_freshness.py` — `fresh` / `stale` record rendering for a multi-row basis
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-tasks/SKILL.md` — § "Pre-Commit Verify Freshness" coverage table and remedy rows
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md` — § "Settle-band position" claim
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/push.md` — § "Freshness precondition" wording and display-detail basis
- OBSERVED: `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness.py` — existing single-row cases that must keep passing
- OBSERVED: `test/plan-marshall/manage-tasks/_pre_commit_verify_freshness_fixtures.py` — ledger-row fixtures the new cases extend
- HYPOTHESIS: `test/plan-marshall/manage-tasks/test_pre_commit_verify_freshness_union_coverage.py` — new module for Deliverables 1, 2 and 4 (verify-at-outline)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-LB-26 on `manage-tasks/SKILL.md` (this plan edits the § "Pre-Commit Verify Freshness" part only) and, conditionally, on `script-shared/scripts/build/_build_execute_factory.py`, where PLAN-LB-26 may bound the daemon hand-back; PLAN-LB-28 on `script-shared/scripts/build/_build_shared.py`, which that plan touches only if it adds test-count result keys; PLAN-LB-22 through its directory-level entries under `phase-6-finalize/standards/`. Sequence against those three.
- May run together with: PLAN-LB-24, PLAN-LB-25 and PLAN-LB-27, and with PLAN-LB-14, PLAN-LB-29, PLAN-LB-30 and PLAN-LB-31.

### Carried sequencing notes

Copied from the source specs. They use the plan ids from before the regrouping; resolve each through
the id map below. Where a carried "Depends on" or "Overlaps with" line disagrees with the bullets above,
the bullets above are current.

From PLAN-LB-12:

- Depends on: none
- Overlaps with: PLAN-LB-13 (`script-shared/scripts/build/` — it edits `_build_jvm_patterns.py` and `_build_parse.py`, and `_build_shared.py` § `cmd_run_common` only if it adds new test-count result keys; this plan edits `_build_execute.py`, `_build_execute_factory.py`, `_build_result.py`, `_build_format.py` and the timeout/killed renderings in `_build_shared.py` § `cmd_run_common`. Sequence the two if PLAN-LB-13's outline takes `_build_shared.py`; otherwise they share no file). PLAN-LB-01 (`phase-6-finalize/standards/pre-push-quality-gate.md` — LB-01 changes what the freshness check accepts from the gate's builds, D5 here changes how the gate invokes them; sequence the two on that one file).
- Adjacent to: PLAN-LB-05 owns the wait procedures (`await-long-running.md`, the standalone-`sleep` prescriptions, the 10-minute call ceiling); this plan changes what a build does when its own limit fires, not how a caller waits for it. PLAN-LB-01 owns the push freshness refusal; a build that this plan makes stop cleanly still produces no green record, and that refusal stays LB-01's subject.
- Left out on purpose: re-tiering whole-tree `verify` to the orchestrator tier; any change to how the learned timeout is computed, keyed, seeded or shared across concurrent plans (`SAFETY_MARGIN`, `compute_weighted_timeout`, the doubling on timeout, per-load budgets); per-checkout serialization in the daemon scheduler (D3 removes the damage an overlap causes without changing admission); classifying a temp-directory-vanished `FileNotFoundError` cluster as `indeterminate` (process-compliance PLAN-25 D1 second half — D3 removes the cause); the pytest per-test timeout budget.

From PLAN-LB-01:

- Depends on: none.
- Overlaps with: none. No other `live-blockers` plan edits these files. PLAN-LB-06 (`PLAN-LB-06-triage-fix-task-loop.md`) edits other scripts in the same `manage-tasks/scripts/` directory (`_tasks_core.py`, `_tasks_crud.py`, `_cmd_step.py`) and adds tests under `test/plan-marshall/manage-tasks/`; the files are disjoint, so the two may run together.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_examined.py` — the union reads `CANONICAL_ANALYSES` and does not change it; PLAN-LB-12 edits neighbouring files in that directory.
- Adjacent to: the gate's own arm selection in `pre-push-quality-gate.md` — untouched; the fix is on the crediting side. Making the gate run `verify` instead was the alternative and is rejected because it would discard the gate's per-arm scoping.
- Left out on purpose: the phase-5 pair from process-compliance PLAN-23 D3 (Step 11c runs one `verify` per affected bundle and Step 12a refuses those rows as `scope_narrower_than_change`). That refusal is on the scope side — per-bundle rows against a change that requires whole-tree — and pooling module scopes would contradict the divergence authority (`resolve_test_scope`). It needs its own decision on what Step 11c should run. The analysis union shipped here applies at Step 12a as well, because both call the same check.
- Left out on purpose: process-compliance PLAN-23 D3 asked that the union be taken only once green evidence is guaranteed to describe a clean checkout (its D1, generated `target/` state feeding tests). That guarantee is not part of this plan. The union does not widen the exposure: a single `verify` row is credited today on the same tree.
- Left out on purpose: a later non-success row at the same SHA for a canonical that also has a green row does not void the green row, today or after this plan. Same behaviour as the single-row rule; not changed here.

### Id map

| Id before the regrouping | Now |
|---|---|
| PLAN-LB-01 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-02 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-03 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-04 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-05 | D1 and D2 to PLAN-LB-25; D3 to PLAN-LB-24; D4 to PLAN-LB-26; D5 to PLAN-LB-22 |
| PLAN-LB-06 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-07 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-08 | PLAN-LB-26 (all deliverables) |
| PLAN-LB-09 | PLAN-LB-25 (all deliverables) |
| PLAN-LB-10 | PLAN-LB-22 (all deliverables) |
| PLAN-LB-11 | PLAN-LB-27 (all deliverables) |
| PLAN-LB-12 | PLAN-LB-23 (all deliverables) |
| PLAN-LB-13 | PLAN-LB-28 (all deliverables) |
| PLAN-LB-14 | unchanged, still PLAN-LB-14 |
| PLAN-LB-15 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-16 | PLAN-LB-30 (all deliverables) |
| PLAN-LB-17 | PLAN-LB-29 (all deliverables) |
| PLAN-LB-18 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-19 | PLAN-LB-24 (all deliverables) |
| PLAN-LB-20 | D1 to D3 to PLAN-LB-30; D4 and D5 to PLAN-LB-31 |
| PLAN-LB-21 | PLAN-LB-31 (all deliverables) |

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-23-verify-builds.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
