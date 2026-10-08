# PLAN-LB-12: A timed-out build leaves its workers running, and nothing names the budget that killed it

epic: live-blockers
workstream: WS-02

> ⛔ **SUPERSEDED — do not launch.** Regrouped on 2026-10-08: PLAN-LB-23 (all deliverables).
> This file is kept as the audit record of the original cut. The successor carries its
> deliverables, claim labels and surface entries unchanged.

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-LB-12-build-timeout-and-verify-budget.md` and is queued as one row file,
> `queue/PLAN-LB-12.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

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

## Deliverables

1. **The daemon stops the whole process tree on timeout.** `run_job` starts the build child in its own
   process group (or session) and, on expiry, signals the group — terminate, a short grace period, then kill —
   instead of the single `proc.kill()`. Done when a new test in
   `test/plan-marshall/build-server/test_marshalld_supervisor.py` runs a child that spawns a grandchild which
   outlives it, lets the supervisor time out, and asserts the grandchild's pid is gone afterwards; the test
   fails at HEAD. The existing `test_run_job_timeout` and the `killed`-vs-`timeout` classification tests stay
   green: a group kill the supervisor sent is still `timeout`, never `killed`.

2. **The in-process build wrapper stops the whole process tree on timeout.** `execute_direct_base` replaces
   its two `subprocess.run(..., timeout=...)` calls with a launch that owns a process group and kills the
   group on expiry, for both capture strategies. Done when a test in
   `test/plan-marshall/script-shared/test_build_execute.py` shows a timed-out command's grandchild is gone
   and the result is still `status: timeout` with the learner fed exactly as today; fails at HEAD. An external
   signal to the wrapper itself (SIGTERM/SIGINT) takes the group down with it — see the verify-first clause on
   SIGKILL.

3. **Pruning the pytest temp root never removes a live run's directory.** `_prune_basetemp_roots` treats a
   per-session directory whose owning build process is still alive as not removable, whatever its age, size
   or position in the keep-count; only directories of finished or dead runs count against the two retention
   bounds. Done when a test in `test/default/test_build_verify.py` creates three session directories, marks
   the oldest as owned by a live pid, makes the newer ones large enough to trip `PYTEST_BASETEMP_MAX_ENTRIES`,
   and asserts the live one survives a prune while a dead-owner directory of the same age is removed; fails at
   HEAD. The retained-history bounds still hold for dead sessions (existing tests stay green).

4. **A timeout or kill result names its bound and the bound's source.** Every `timeout` and `killed` build
   result carries `timeout_used_seconds` = the bound actually applied, plus `timeout_source`
   (`explicit` | `learned` | `default` | `floor` | `daemon_default`) and the `command_key` the learned value
   was read under; the routed leg reports the bound, not the elapsed time. Done when (a) a routed timeout
   whose job ran 300 s under an 1800 s daemon bound renders `timeout_used_seconds: 1800`,
   `timeout_source: daemon_default` (at HEAD it renders the duration), (b) an in-process timeout under a
   learned value renders `timeout_source: learned` with the key, and (c) the three fields survive
   `_build_format` filtering into the printed TOON; tests in `test_build_timeout_truthfulness.py` and
   `test_explicit_timeout_routing.py`.

5. **Gate builds are attributed to their plan.** The builds the finalize gates run (pre-push quality gate,
   and any other finalize step that runs an architecture-resolved `executable` verbatim) carry the plan's id,
   so the daemon job row, the build log directory and the `[BUILD-SERVER] resolved build` line all name the
   plan instead of `NO_PLAN`. Done when a test resolves a build command for a plan, applies the documented
   gate invocation, and asserts the submitted `plan_id` equals the plan; plus a doc-contract test that no
   shipped finalize standard instructs running a resolved build executable without the plan-id step.

## Claim Labels

- OBSERVED: the daemon's timeout path kills one process — `proc = await asyncio.create_subprocess_exec(...)` is created without `start_new_session`/`process_group`, and expiry runs `proc.kill()` then `proc.wait()` — read at `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_supervisor.py:313-332` § `run_job`
- OBSERVED: the daemon child is not the test runner but a chain — `python3 .plan/execute-script.py <notation> run …` re-running the build wrapper, which runs `./pw`, which runs `uv run pytest` with xdist workers — so one `kill()` reaches only the first link; read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:767` § `_route_to_daemon` and `build.py:305-310` § `run`
- OBSERVED: the in-process leg has the same fault — both branches call `subprocess.run(cmd_parts, timeout=timeout_seconds, …)`, whose expiry kills only the direct child — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute.py:259-280` § `execute_direct_base`
- OBSERVED: no process-group handling exists anywhere on the build path — a search of `script-shared/scripts/build/`, `manage-build-server/scripts/`, `build-server-client/scripts/` and `build.py` for `start_new_session|killpg|setsid|getpgid` finds only the daemon's own daemonization (`marshalld.py:238`, `manage_build_server.py:275`)
- OBSERVED: every pytest invocation gets its own directory `.plan/temp/pytest-basetemp/{pid}-{uuid4}` and prunes the shared root first — read at `build.py:264-291` § `_prepare_session_basetemp`
- OBSERVED: the prune protects only the newest directory; any older one is removed when it falls outside `PYTEST_BASETEMP_KEEP = 3` or when the running entry total would pass `PYTEST_BASETEMP_MAX_ENTRIES = 100_000`, with no check that its owner is still running — read at `build.py:190-261` § `_prune_basetemp_roots` (the newest-dir exception and its `popen-gwN` symptom comment are at `:236-249`)
- OBSERVED: the source comment sizes one whole-tree session at about 92,000 entries, so two overlapping whole-tree runs in one checkout exceed the 100,000-entry budget and the older, still-running one is the removal candidate — read at `build.py:128-149`
- HYPOTHESIS: the pid in the directory name is the `build.py` process, which stays alive for the whole pytest run because `run()` blocks in `subprocess.run`, so `os.kill(pid, 0)` is a sound liveness probe — confirm/refute at `build.py` § `_prepare_session_basetemp` and § `cmd_module_tests`/`cmd_coverage` (verify-at-outline)
- HYPOTHESIS: the overlap that triggers the deletion is two runs in the SAME checkout (the root is a cwd-relative path, so separate worktrees have separate roots), admitted concurrently because the scheduler checks only the global slot — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_scheduler.py` § `admit_next` (verify-at-outline)
- OBSERVED: a routed timeout reports its elapsed time as the bound — `timeout_result(duration, duration, log_file, command_str)` passes `duration` as `timeout_used_seconds` — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py:631-632` § `_daemon_result_to_direct` and `:696-697` § `_result_for_log_verdict`
- OBSERVED: the routed `killed` result carries no bound at all (`killed_result(exit_code=…, duration_seconds=…, log_file=…, command=…)`) — read at `_build_execute_factory.py:633-645`
- OBSERVED: no result names where a bound came from — `timeout_source` has zero hits under `script-shared/scripts/build/` and `manage-build-server/scripts/`; `timeout_used_seconds` is the only bound field (`_build_result.py:370-400`, `_build_format.py:44`)
- OBSERVED: the applied bound has four possible origins that the result cannot distinguish — explicit `--timeout`, a persisted value times `SAFETY_MARGIN = 1.25`, the tool default, or a floor (`MINIMUM_TIMEOUT_SECONDS = 120`, `min_timeout`) — read at `marketplace/bundles/plan-marshall/skills/manage-run-config/scripts/run_config.py:244-274` § `timeout_get` and `_build_execute.py:237-240`
- OBSERVED: the daemon's own bound is a fifth origin — `_DEFAULT_JOB_TIMEOUT = 1800`, raised to `requested + 30` only when the submit stated a bound — read at `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py:73-91,600-619` § `_resolve_job_timeout`
- HYPOTHESIS: the recorded "killed at 783 s against a measured 1434 s" was the child's own learned bound (a persisted ~627 s × 1.25) and the 1434 s figure was read after the timeout path doubled the stored value (`timeout_set(command_key, min(timeout_seconds * 2, MAX_TIMEOUT))`), i.e. the two numbers are the same key before and after — confirm/refute at `_build_execute.py:337-342` and `run_config.py:237-241,319-328` (verify-at-outline)
- OBSERVED: an absent `--plan-id` becomes the `NO_PLAN` sentinel for every build-class handler — read at `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_cli.py:692-701` § `build_main`, and is what the daemon is told (`routing_plan_id = plan_id or NO_PLAN_SENTINEL`, `_build_execute_factory.py:773`)
- OBSERVED: the pre-push gate resolves each build with `architecture resolve … --audit-plan-id {plan_id}` and then runs "the captured `executable` verbatim"; no step adds `--plan-id` to that executable — read at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/pre-push-quality-gate.md:240-245,257-268,307-314`
- OBSERVED: `--audit-plan-id` is consumed by the generated executor for its own log line and stripped before the script runs, so it never reaches the build wrapper — read at `marketplace/bundles/plan-marshall/skills/tools-script-executor/templates/execute-script.py.template:1344-1376` § `extract_audit_plan_id`
- OBSERVED: a helper that inserts `--plan-id` after `run` for build notations exists but belongs to the execute phase — read at `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py:106-169` § `inject_project_dir`
- HYPOTHESIS: `architecture resolve` returns an `executable` with no `--plan-id` even when called for a plan, so attribution can be fixed either in the resolver (emit the flag when a plan id is supplied) or in the gate document (apply the existing helper) — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_handlers.py` § `cmd_resolve` (verify-at-outline)
- Verify-first clause: decide the kill mechanism before scoping D1/D2. A new session detaches the build from the caller's process group, so a harness that SIGKILLs the wrapper can no longer reach the build through the group; a handler can forward SIGTERM/SIGINT/SIGHUP but not SIGKILL. Settle whether the wrapper uses a new process group with signal forwarding, and state in the result or the log what an un-forwardable kill leaves behind. Do not ship a variant that makes a harness reap leave MORE processes than today.
- Verify-first clause: D1 and D2 are POSIX mechanisms (`os.killpg`). State the Windows behaviour explicitly (unchanged single-process kill is acceptable) rather than leaving it undefined.
- Verify-first clause: D3 must fail safe. An unreadable or unparsable owner pid, or a pid that was reused by an unrelated process, must resolve to "keep", never to "remove"; the cost of a wrong "keep" is one extra retained directory, the cost of a wrong "remove" is a destroyed run.
- Verify-first clause: for D5, enumerate every shipped workflow document that runs a resolved build `executable` (not only the pre-push gate) from a search of `marketplace/bundles/plan-marshall/skills/**/*.md` for the resolve-then-run pattern, and fix the set that search returns; do not assume the gate is the only site.

## Expected Surface

- DERIVED — this spec is superseded and claims no surface of its own. The entries it declared are
  recorded in the next section and are now declared by the successor named in the banner above.

## Superseded Surface (record only)

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

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-LB-13 (`script-shared/scripts/build/` — it edits `_build_jvm_patterns.py` and `_build_parse.py`, and `_build_shared.py` § `cmd_run_common` only if it adds new test-count result keys; this plan edits `_build_execute.py`, `_build_execute_factory.py`, `_build_result.py`, `_build_format.py` and the timeout/killed renderings in `_build_shared.py` § `cmd_run_common`. Sequence the two if PLAN-LB-13's outline takes `_build_shared.py`; otherwise they share no file). PLAN-LB-01 (`phase-6-finalize/standards/pre-push-quality-gate.md` — LB-01 changes what the freshness check accepts from the gate's builds, D5 here changes how the gate invokes them; sequence the two on that one file).
- Adjacent to: PLAN-LB-05 owns the wait procedures (`await-long-running.md`, the standalone-`sleep` prescriptions, the 10-minute call ceiling); this plan changes what a build does when its own limit fires, not how a caller waits for it. PLAN-LB-01 owns the push freshness refusal; a build that this plan makes stop cleanly still produces no green record, and that refusal stays LB-01's subject.
- Left out on purpose: re-tiering whole-tree `verify` to the orchestrator tier; any change to how the learned timeout is computed, keyed, seeded or shared across concurrent plans (`SAFETY_MARGIN`, `compute_weighted_timeout`, the doubling on timeout, per-load budgets); per-checkout serialization in the daemon scheduler (D3 removes the damage an overlap causes without changing admission); classifying a temp-directory-vanished `FileNotFoundError` cluster as `indeterminate` (process-compliance PLAN-25 D1 second half — D3 removes the cause); the pytest per-test timeout budget.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/live-blockers/plans/PLAN-LB-12-build-timeout-and-verify-budget.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
