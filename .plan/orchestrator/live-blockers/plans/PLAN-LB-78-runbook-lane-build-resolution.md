# PLAN-LB-78: The runbook lane runs the project's own resolved build commands, through the build server

epic: live-blockers
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall-runbook-lane` hand-off.
> Lives at `plans/PLAN-LB-78-runbook-lane-build-resolution.md` and is queued as one row file,
> `queue/PLAN-LB-78.json`, in the epic ledger. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer
> and carries no brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

> Staged from an operator datapoint (a runbook-lane run in a Maven consumer repository asked how the
> build gate should run, because `resolve` supplied `quality-gate`, `module-tests`, `verify` and
> `test-compile` and the installed executor handed them to Maven literally, failing with
> `Unknown lifecycle phase "quality-gate"`), and from the operator decision that **the lane uses the build
> server**. Priority is **high**: the lane cannot run in any non-pyproject project today, and the epic's
> goal names consumer repositories. **Each deliverable is its own outline deliverable, and each Done-when is
> its own success criterion. Do not merge them.** A Done-when says "fails at `e1481166c`" only where the
> behaviour is new at that sha; a clause that already holds says "holds at `e1481166c`".

## Objective

The runbook lane's `resolve` composes every build command as the build wrapper plus
`run --command-args "<canonical name>"`, for any build system. The pyproject wrapper maps canonical names;
the Maven wrapper takes complete Maven arguments, so the lane's build gate fails in a Maven project, and the
same shape should fail for Gradle and npm. The architecture already resolves the correct command per
canonical and module (`quality-gate` → `verify -Ppre-commit …`, `test-compile`, `module-tests`), and the lane
bypasses it. Separately, the lane forbids the build server and forces every build in-process, on the stated
ground that the worktree has no executor; the operator states that every worktree has its own
`execute-script`, so that ground is wrong. This plan makes `resolve` return the architecture's own
resolution, and makes the lane build through the build server with a recorded in-process fallback.

## Deliverables

1. **`resolve` returns each build command as the architecture's own resolution.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester
   - Persona: plan-marshall:persona-implementer
   - In `runbook_lane.py` `_resolve_build`, each of `quality-gate`, `module-tests`, `verify` and
     `test-compile` is resolved through the architecture's `resolve_command` for that canonical, so the
     returned string is the complete command the build system's wrapper accepts. The composed
     `--command-args "{canon}"` form is removed. A canonical the architecture cannot resolve for the
     project fails closed with a named code (`build_command_unresolvable`, naming the canonical); the lane
     never falls back to a composed string and never to a default build. Decide at outline how the lane
     scopes a multi-module project (the module the change touches, or the root), record why, and keep the
     `split` list.

   *Done when:* each of these fails at `e1481166c`:
   - for a Maven fixture project, the resolved `quality-gate` is the architecture's `verify -Ppre-commit`
     form and no resolved command carries a bare canonical name as its `--command-args`;
   - for a Maven fixture project, `module-tests` and `test-compile` are the architecture's `test` and
     `test-compile` forms;
   - a canonical the architecture cannot resolve returns `build_command_unresolvable` naming it, and no
     `build` map is returned;
   - for a pyproject fixture the resolved commands still run through the pyproject wrapper (this clause
     **holds at** `e1481166c`, kept as the preservation guard).

2. **The lane builds through the build server, with a recorded in-process fallback.**
   - Skills: pm-plugin-development:plugin-architecture, pm-plugin-development:plugin-script-architecture, pm-dev-python:python-core, plan-marshall:ref-code-quality, pm-dev-python:pytest-testing, plan-marshall:persona-module-tester, pm-documents:ref-documentation
   - Persona: plan-marshall:persona-implementer
   - `runbook-lane/SKILL.md` section 2 and section 4 stop forbidding the daemon. Every build runs with the
     default routing (`--execution-mode auto`) against the worktree, whose own `execute-script` the daemon
     uses; the sentence that the worktree has no executor and the rule "never drop
     `--execution-mode in_process`" are removed or rewritten to what is true.
   - The lane runs the build server's `preflight` once at setup and records `ready`, `disabled` or `down`
     in the progress file and the landing message. A `degraded` build falls back in-process and the landing
     records the degradation and its `reason`; a `killed` job is never blind-retried; a daemon-routed build
     is never backgrounded, and a `running` result is re-attached with a bounded wait, per the
     build-server client's own prohibitions (cited, not restated).
   - `resolve` reports the build server state (`build_server: ready|disabled|down` with the `reason`) so
     the lane reads it from the resolve result rather than guessing. An unenrolled project is `disabled`,
     not an error: enrolment stays an operator action in `manage-build-server`.
   - The shell-timeout paragraph and the split form stay for the in-process fallback only.

   *Done when:* doc and resolve tests assert, each failing at `e1481166c`:
   - `SKILL.md` no longer contains "never use the daemon" or the claim that the worktree has no executor,
     and states the `preflight` step, the `degraded` fallback record and the `killed` rule;
   - the section 4 build-gate commands carry no `--execution-mode in_process`;
   - `resolve` returns `build_server` with the preflight outcome for a fixture project that is
     unenrolled (`disabled`), enrolled and reachable (`ready`) and enrolled with the daemon down (`down`).

## Claim Labels

- OBSERVED: `_resolve_build` composes `{prefix} {notation} run --command-args "{canon}"` for `quality-gate`, `module-tests`, `verify` and `test-compile`, probing only `verify` at module level — `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` L407-439.
- OBSERVED: the Maven wrapper's `--command-args` is "Complete Maven command arguments (e.g., 'verify -Ppre-commit -pl my-module')" — `maven run --help`.
- OBSERVED: discovery emits `quality-gate` as `verify -Ppre-commit -pl {module}`, `module-tests` as `test -pl {module} -am` and `test-compile` as `test-compile -pl {module} -am` for a module with tests — `marketplace/bundles/plan-marshall/skills/extension-api/standards/canonical-commands.md` § Extension Implementation and `build-maven/standards/maven-impl.md` § Test ladder.
- OBSERVED: the lane forbids the daemon and states "the worktree has no executor of its own" — `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` L281-285 and L343.
- OBSERVED: the operator states that every worktree has its own `execute-script` (operator, 2026-10-20), and a PLAN-LB-59 reviewer session built through the daemon from a worktree cwd with the worktree's executor (`mechanism=daemon_longpoll`; landing analysis of PLAN-LB-59).
- OBSERVED: the build-server client's `submit` takes `--exec-path` separately from `--project-path`, is fail-soft (`degraded` → in-process), and prohibits backgrounding a daemon-routed build — `marketplace/bundles/plan-marshall/skills/build-server-client/SKILL.md`.
- OBSERVED: the Maven wrapper's `--execution-mode` defaults to `auto` — `maven run --help`.
- OBSERVED: the datapoint — a runbook-lane run in a Maven consumer repository received `quality-gate`, `module-tests`, `verify` and `test-compile` from `resolve` and failed with `Unknown lifecycle phase "quality-gate"` (operator, 2026-10-20; the run's resolve output was not read by the orchestrator).
- HYPOTHESIS: `resolve_command(canon, module, project_dir)` returns the complete wrapper command for `test-compile` on a Maven project, not only for the three canonicals the lane already probes — confirm at `manage-architecture/scripts/_cmd_client_query.py` § `resolve_command` (verify-at-outline).
- HYPOTHESIS: `--execution-mode auto` routes to the daemon only for an enrolled project with a verified handshake and otherwise runs in-process — confirm at `script-shared/scripts/build/_build_execute_factory.py` (verify-at-outline).
- Verify-first clause: confirm by one routed build that the daemon builds a worktree through the worktree's own executor, and record which `--exec-path` and `--project-path` the routing used and why the old "no executor" rule held; a refutation loops back to re-scope D2.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/scripts/runbook_lane.py` — `_resolve_build`, the `resolve` payload (D1, D2)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/runbook-lane/SKILL.md` — sections 0, 2 and 4, the canonical invocations (D1, D2)
- OBSERVED: `test/plan-marshall/runbook-lane/test_runbook_lane.py` — the resolve and doc-contract tests (D1, D2)

## Dependencies and Sequencing

- Depends on: PLAN-LB-72 (shipped, `cf28a05db`).
- Overlaps with: the staged PLAN-LB-73 on all three entries above. **This plan goes first**: it rewrites the
  build-gate section PLAN-LB-73's lane-text fixes sit beside. The emit gate decides.
- Adjacent to: `build-server-client` and `manage-build-server` (consumed, never changed here); the lane's
  `build-classify` verb (unchanged).

## Hand-Off Command

```text
/plan-marshall-runbook-lane plan=.plan/orchestrator/live-blockers/plans/PLAN-LB-78-runbook-lane-build-resolution.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
