# PLAN-LB-104: A routed build resolves the tree the caller named, so the runbook lane builds through the build server by default

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-104-routed-build-project-dir.md` and is queued as one row file, `queue/PLAN-LB-104.json`,
> in the epic ledger. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from the operator's instruction on 2026-10-29: "On some of the plans I saw the runbook lane does not use the build-server.
> This should be the default." The operator's earlier ruling stands: the lane uses the build server. This is operator-requested
> work, staged above the live-blockers focus rule; the defect it fixes sat in the epic's Watches for six landings (LB-53, LB-55,
> LB-82, LB-96, LB-58, LB-100) as "recorded, not staged".

## Objective

A routed build submits the executor-form command to the daemon with the caller's own `--project-dir` token unchanged. The daemon
runs that command with its working directory set to the absolute worktree, so a RELATIVE `--project-dir` (which is what the lane's
text and `runbook_lane resolve` hand every build: `.plan/local/worktrees/{plan_id}`) is re-resolved against the worktree instead of
the main checkout. It names a directory that does not exist, the wrapper (`pw`, `mvnw`) is not found there, the wrapper lookup
falls through to a bare system command (`pwx`, `mvn`) that is not installed, and the job dies `execution_failed`, exit -1. The lane
then runs every later build in-process, which is why some plans do not use the build server. This plan fixes the cause in the
shared build client so every caller and every build tool is covered, makes the failure say what it looked at, and stops the lane
from abandoning the server for a whole run after one routed failure.

## Deliverables

1. **The submitted command names the tree the caller named, in absolute form.**
   - In `_route_to_daemon` the reconstructed command (`python3 {exec_root}/.plan/execute-script.py {notation} *sys.argv[1:]`)
     replaces the value of `--project-dir` with `exec_root`, for both token forms (`--project-dir X` and `--project-dir=X`).
     No other token is touched; an argv with no `--project-dir` is submitted unchanged, because the child's default `.` already
     resolves to `exec_root` (the daemon sets the child's working directory to `exec_root`).
   - Every other path-valued flag the routed argv can carry is checked and either proven cwd-independent or normalised the same
     way; the result is recorded in the PR (`--plan-id` is mutually exclusive with `--project-dir` and derives its own tree;
     `--working-dir` and `--env` are the npm extras).

   *Done when:* a routing test with `sys.argv` carrying a relative `--project-dir` asserts the submitted argv carries the absolute
   one and that no other token changed; a second test, through the REAL resolver and not a stub, builds a tmp tree holding a `pw`
   file, takes the submitted argv, and shows `detect_wrapper` resolving `./pw` from that tree as the working directory — and the
   same test is red at HEAD (it resolves the system fallback or nothing). The PR records one live routed build run from a real
   lane worktree with the relative form (`--project-dir .plan/local/worktrees/{id}`), whose result reports the daemon mechanism
   and no degradation. The daemon in use is stale (`manage-build-server status` reports `binary_diverges`); the fix is client-side
   and runs in the worktree's own executor, so no daemon restart is part of this plan.

2. **A missing wrapper is a named failure, not an opaque `execution_failed`.**
   - The `FileNotFoundError` leg of `_build_execute.py` already builds the message `{tool} wrapper not found: {wrapper}`, but the
     rendered result carries only `error: execution_failed`, so six landings could not tell a missing wrapper from a daemon fault.
     The rendered result (TOON and JSON, in-process and routed leg alike) carries the reason, the wrapper name tried and the
     project directory it looked in.
   - A routed job whose inner result is `execution_failed` is reported as that, with the inner reason, and not as a generic build
     failure.

   *Done when:* a test that points a build at a directory with no wrapper and no system fallback shows a result naming the wrapper
   and the directory, on the in-process leg and on the routed leg (the routed leg through a stub job whose log holds that inner
   result); both are red at HEAD.

3. **The lane routes every build and never turns the server off for the rest of the run.**
   - `runbook-lane/SKILL.md` § 4 states: the default routing (no `--execution-mode` flag) is used for every build; a routed build
     that fails with a launch fault (`execution_failed`, which is not a red build) is re-run ONCE for that build with
     `--execution-mode in_process`, recorded with its reason, and the NEXT build is submitted routed again;
     `--execution-mode in_process` as a standing setting is allowed only where `build-routing` answers `in_process`.
   - The landing's build-server line records the number of builds per reported `mechanism` (daemon versus in-process), so a run
     that did not use the server is visible in the landing and not found afterwards in the daemon journal.

   *Done when:* the SKILL text carries the three statements and a guard test in `test_runbook_lane.py` pins them; the landing
     template line for the build server names the per-mechanism count.

Split guard: three deliverables, one theme (the lane builds through the server). D2 and D3 do not stand alone — D2 is how a
future launch fault is recognised, D3 is what the lane does about one — and D1 is the fix; they ship together.

## Standing Constraints

- Operator ruling: the runbook lane uses the build server by default. Do not add a lane-side switch that turns it off.
- Fix the cause in the shared build client (`_build_execute_factory.py`), not in the lane. Do not change `runbook_lane resolve`'s
  `worktree` field or its relative form: other consumers read it, and the client fix removes the dependency on the caller's form.
- Do not change the daemon, the supervisor or the daemon's clean-environment whitelist (`BASELINE_ENV_KEYS`). A bare system
  fallback that is missing from the daemon's PATH is a separate, second possible cause for a project with no wrapper (see
  Claim Labels); this plan records whether it exists and does not widen the whitelist.
- Do not change `--execution-mode` semantics (`auto`, `in_process`, `daemon`) or `build-routing`.
- Every new or changed test states what it protects; a test of the routed argv goes through the real resolver, not a stub that
  would pass at HEAD.
- Sonar is not enabled for this project and is ignored: collect no Sonar figure and require none.

## Claim Labels

- OBSERVED: a routed job that failed and one that succeeded differ in the form of `--project-dir`, with the same daemon and executor.
  The failing job's journal row (`~/.plan-marshall/marshalld/journal/1c6ce5214ded441fa42bea75b0005635.json`) holds
  `--project-dir .plan/local/worktrees/lb-100-merge-path-truth` with `project_path` the absolute worktree; its job log reads
  `[EXEC] pwx quality-gate plan-marshall`, `error: execution_failed`, `exit_code: -1`, `duration_seconds: 0`. The passing job
  (`.../journal/05cc7d649d274c0fae035da9bb8833f8.json`) holds an absolute `--project-dir` and its log reads
  `[EXEC] ./pw module-tests plan-marshall`, 27370 tests, success.
- OBSERVED: the client rebuilds the command from its own argv tail and the daemon runs it with the worktree as the working directory —
  `_build_execute_factory.py` L920-923 (`command = ['python3', .../execute-script.py, notation, *sys.argv[1:]]`) and
  `_marshalld_supervisor.py` L429-436 (`create_subprocess_exec(*command, cwd=cwd, env=child_env, ...)`), where `cwd` is
  `spec.project_path` (`marshalld.py` L638-645).
- OBSERVED: wrapper detection resolves `project_dir` against the process's working directory and, when no wrapper file exists
  there, returns the system fallback only if it is on PATH, and the caller then substitutes the bare fallback name anyway —
  `_build_execute.py` L52-86 (`detect_wrapper`) and `_build_execute_factory.py` L1189-1201 (`return wrapper or config.system_fallback`).
  The fallbacks are `pwx` (`_pyproject_execute.py` L84) and `mvn` (`_build_execute_factory.py` L16-18).
- OBSERVED: the lane hands the build a relative path — `runbook-lane/SKILL.md` L507-509 (`--project-dir {worktree}`) and
  `runbook_lane.py` L2162 (`worktree = f'.plan/local/worktrees/{plan_id}'`); the text nowhere says "absolute".
- OBSERVED: the epic already records the trigger and the history — `epic.md` Watches "Routed-build failure from a worktree has a known
  trigger (PLAN-LB-97)" (72 routed builds clean once the path was absolute) and "Routed builds from a lane worktree still fall back
  to in-process after PLAN-LB-92" (LB-53, LB-55, LB-82, LB-96, LB-58). The LB-92 premise (an absent worktree executor) was a
  different, earlier defect; the executor path in the submitted command is already absolute.
- OBSERVED: the rendered failure drops the reason — the job log of the failing job carries `error: execution_failed` and no
  "wrapper not found" text, while `_build_execute.py` L521-532 builds that text.
- OBSERVED: builds run from a worktree working directory with no `--project-dir` route cleanly (the PLAN-LB-77 and PLAN-LB-76
  sub-agent builds, `mechanism=daemon_longpoll`), consistent with the default `.` resolving to the worktree.
- HYPOTHESIS: the Maven failure the operator quoted ("execution_failed ... it invokes bare mvn", from another project's lane) is the
  same defect, because `detect_wrapper` is shared and the Maven fallback is `mvn`. Not observed here — that project's daemon
  journal was not read. Refute by reading its failing job's `--project-dir`; if it is absolute, the cause is the daemon's PATH
  (no `mvnw`, `mvn` not on the daemon's whitelisted PATH) and needs its own deliverable (verify-at-outline, journal row of that job).
- HYPOTHESIS: the rendered result drops the message because the result formatter keeps only known fields — confirm at
  `_build_result.py` (the formatter that renders `error_result` / the execute dict) and at the `FileNotFoundError` leg in
  `_build_execute.py` L521 (verify-at-outline).
- HYPOTHESIS: a routed job's inner `execution_failed` is rendered as `build_failed` with exit code 1 — the journal row's `result.exit_code`
  is 1 and `_daemon_result_to_direct`'s failure leg uses `ERROR_BUILD_FAILED` (`_build_execute_factory.py` L731-744); confirm
  whether `read_log_verdict` exposes the inner error type (verify-at-outline).
- HYPOTHESIS: no other flag in the routed argv is cwd-sensitive — `--plan-id` and `--project-dir` are mutually exclusive
  (`_build_cli.py` `add_project_dir_arg`), and `--working-dir` is read relative to the project directory for npm; confirm in
  `_build_cli.py` L25-110 and the npm build skill's execute config (verify-at-outline).
- HYPOTHESIS: the lane's "every later build in-process" after one failure is the lane improvising, not a rule in the text —
  `SKILL.md` L512-525 prescribes `in_process` only for an absent executor slot; confirm no other passage says it
  (verify-at-outline, `runbook-lane/SKILL.md`).
- HYPOTHESIS: the landing template's build-server line sits at `runbook-lane/SKILL.md` L859 and in the landing payload template —
  confirm where the per-mechanism count belongs and that `inbox landing-check` does not require a new key
  (verify-at-outline, `runbook-lane/SKILL.md` § 8 and `persona-plan-orchestrator`'s landing template).
- Verify-first clause (D1): before editing, reproduce the failure with the SAME shape, a routed build from the main checkout with a
  relative `--project-dir` naming an existing worktree, and read its journal row; if it succeeds, the trigger is not the form of the
  path and this spec is wrong at its centre — loop back and re-scope.
- Verify-first clause (D3): settle the Maven question above before writing D3's wording, so the lane text does not describe one cause
  for two.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — `_route_to_daemon` argv reconstruction (D1), routed failure leg (D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute.py` — the wrapper-not-found result (D2)
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` — the rendered failure fields (D2; verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — § 4 routing text and the landing's build-server line (D3)
- OBSERVED: `test/plan-marshall/build-server/test_build_execute_routing.py` — the submitted-argv tests (D1)
- OBSERVED: `test/plan-marshall/script-shared/test_build_execute_factory.py` — the real-resolver and wrapper-not-found tests (D1, D2)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the guard test for the lane text (D3)

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none declared. PLAN-LB-101 and PLAN-LB-103 are running and touch the finalize gate and the project config tests; none of the surface above is theirs. If a census or outline finds one, sequence this plan after the collision.
- Adjacent to: `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md` L194-200 (describes the argv rebuild for `--timeout`; add one sentence if D1's wording belongs beside it, else leave); the daemon and supervisor (untouched); `runbook_lane resolve` (untouched); the daemon's stale-binary state (`binary_diverges`), which is an operator step in `manage-build-server` and not this plan's.

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-104-routed-build-project-dir.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
