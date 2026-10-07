# PLAN-06: Route pyproject builds through the daemon (pyproject-routing-integration)

epic: plan-server
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> The orchestrator EMITS the command below; it never launches the plan inline.

## Objective

The pyproject build adapter never routes to marshalld. The daemon epic's core thesis
is that this repo's long, reap-exposed builds (`./pw` = `pyproject_build`) should route
to a machine-level owner so a killed session-side waiter re-polls a surviving job
instead of destroying real work. That thesis is **structurally unrealized for the
plan-marshall repo itself**, because the pyproject adapter bypasses the routing seam:

- `create_execute_handlers()` (`_build_execute_factory.py`) returns `(execute_direct, cmd_run)`.
  The **second** element (`cmd_run`, ~L648) is the routing handler — it runs
  `_route_to_daemon` first, records the requested-vs-resolved line via `_record_resolution`,
  and only falls back to an in-process `execute_direct(...)` inside `build_queue_slot` when
  routing did not happen.
- **Maven / npm / gradle** wire `execute_direct, cmd_run = create_execute_handlers(...)` —
  they USE the factory's routing `cmd_run`, so they route and (post-PLAN-05) emit the
  captured resolution line.
- **Pyproject** (`_pyproject_execute.py:76`) wires `_inner_execute_direct, _ = create_execute_handlers(...)`
  — it **discards the routing `cmd_run` into `_`** and defines its OWN local `cmd_run`
  (L154) that wraps ONLY `build_queue_slot(plan_id)` around a self-heal `execute_direct`.
  No `_route_to_daemon`, no `_record_resolution`, and `plan_id` is not even forwarded into
  `execute_direct`. The adapter did this to add the one-shot `.pyprojectx`-cache-corruption
  self-heal retry, but in doing so it lost the daemon-routing path.

**Consequence (verified against ground truth, PLAN-05 landing `landings/PLAN-05.md`):**
every `pyproject_build` — `./pw`, quality-gate, verify, coverage, module-tests — runs
in-process unconditionally regardless of daemon liveness/registration, emits no
`[BUILD-SERVER] resolved build` line at all, and leaves zero daemon interaction-audit
records. This is the fully-explained root cause of the epic's OBSERVED-NEGATIVE
worktree-routing watch (world 1: structural call-site bypass) and of the daemon's idle
audit log during this repo's build-heavy phases.

This plan re-threads daemon routing THROUGH the pyproject adapter so a registered-worktree
pyproject build routes exactly like a maven build does, WITHOUT losing the self-heal retry.

## Deliverables

1. **Route pyproject through the factory routing path, preserving the self-heal retry.**
   The pyproject build must attempt `_route_to_daemon` first (in `auto`/`daemon` mode),
   record the requested-vs-resolved resolution line, and fall back to the in-process
   self-heal executor + `build_queue_slot` only when routing did not happen — the same
   route-then-fallback ordering maven already gets from the factory `cmd_run`. `plan_id`,
   `execution_mode`, `env_vars`, and `working_dir` MUST be forwarded intact so the daemon's
   S2 compatibility guard (`daemon_incompatible`) and `execution_mode=daemon` fail-loud
   behave identically to the other adapters. The MECHANISM is an OUTLINE decision — the
   natural seam is to let the factory's routing `cmd_run` call an injected/overridable
   in-process executor (so pyproject supplies its self-heal wrapper as that executor)
   rather than duplicating the routing prefix in the adapter — but the outline chooses;
   the hard requirement is that pyproject END UP on the factory's single routing path,
   with the self-heal retry intact on the in-process leg, and NO second copy of the
   routing/`_record_resolution` logic.
2. **Regression tests.** Assert, at the seam: (a) a registered-worktree `auto`-mode
   pyproject build ROUTES to the daemon (submit boundary reached / `resolved=routed`
   recorded) — the case that is impossible today; (b) the in-process fallback STILL fires
   the one-shot `.pyprojectx` self-heal retry on the documented corruption symptom
   (no regression of the behavior the adapter override existed for); (c) a plan-less
   pyproject build runs unchanged (queue-slot NO-OP passthrough); (d) `execution_mode=daemon`
   with a daemon-incompatible env/working-dir fails loud, matching maven. Reuse the
   `execution_mode=in_process` hermetic-declaration pattern from PLAN-04 D5 so these tests
   stay daemon-state-independent where they must.
3. **Doc note (fold, do not split).** Update the owning build-architecture doc surface so
   the "pyproject routes like the other adapters" fact is recorded and the earlier
   pyproject-specific divergence is not silently re-introduced. Cross-reference, not
   duplication.

Split guard: 3 deliverables — well under the threshold. D2/D3 are the test and doc surfaces
of the single wiring change in D1.

## Expected Surface

- `marketplace/bundles/plan-marshall/skills/build-pyproject/scripts/_pyproject_execute.py`
  — stop discarding the routing handler; route pyproject through the factory routing path
  with the self-heal executor on the in-process leg; forward `plan_id`/`execution_mode`/
  `env_vars`/`working_dir`.
- `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py`
  — likely a small extension so the factory routing `cmd_run` accepts an overridable
  in-process executor (the injection seam), IF the outline picks that mechanism. Shared
  with maven/npm/gradle — must stay byte-behaviour-identical for them.
- The script-shared / build-server test surface (D2).
- `doc/developer/build-architecture.adoc` (D3).

## Dependencies and Sequencing

- Depends on: nothing staged in this epic (PLAN-05 shipped; queue otherwise drained).
- **Cross-epic surface adjacency — plan-optimization PLAN-32** (truthful-build-timeout-accounting)
  touches `_build_execute.py` + `manage-run-config/run_config.py` in the same build-emit
  module family; this plan touches `_pyproject_execute.py` + possibly `_build_execute_factory.py`.
  File-level mostly disjoint, BUT if this plan extends `_build_execute_factory.py` and PLAN-32
  also does, watch for rebase adjacency on shared imports/signatures in
  `script-shared/scripts/build/`. Coordinate at outline: reuse, do not duplicate, any shared
  seam. Note #972 (attach-test-evidence-to-timeout-killed-status) has already landed on main.
- **Regression risk:** the factory routing `cmd_run` is shared by maven/npm/gradle. Any
  change to it MUST preserve their exact current behaviour — the D2 suite should include a
  guard that the other adapters' routing path is unchanged, or the mechanism must be
  additive (an optional override defaulting to today's inner executor).

## Design Notes

- **Not a runtime guard / not a bypass knob.** The fix is to put pyproject ON the existing
  routing path — a wiring/config fix — NOT an env-var opt-in or a `[HINT]` layer. Do not
  reintroduce anything shaped like the removed `require_wrapper` global opt-out.
- **This closes the epic's central routing gap.** Once pyproject routes, the worktree-container
  routing path is finally exercisable from this repo (today only maven consumers like
  API-Sheriff exercise it). A registered-worktree pyproject build that routes + leaves an
  interaction-audit record is the proof the OBSERVED-NEGATIVE watch never got.

## Hand-Off Command

```text
/plan-marshall task="The pyproject build adapter never routes to the marshalld daemon, so every pyproject_build in this repo (./pw, quality-gate, verify, coverage, module-tests) runs in-process unconditionally and the daemon's work-preservation thesis is unrealized for plan-marshall itself. Root cause (verified): create_execute_handlers() in script-shared/scripts/build/_build_execute_factory.py returns (execute_direct, cmd_run) where the SECOND element cmd_run is the routing handler (runs _route_to_daemon, records _record_resolution, falls back to in-process execute_direct inside build_queue_slot). Maven/npm/gradle wire 'execute_direct, cmd_run = create_execute_handlers(...)' and USE the routing cmd_run. But build-pyproject/scripts/_pyproject_execute.py:76 wires '_inner_execute_direct, _ = create_execute_handlers(...)' — it DISCARDS the routing cmd_run into _ and defines its own local cmd_run (line 154) that wraps only build_queue_slot(plan_id) around a self-heal execute_direct, with no _route_to_daemon, no _record_resolution, and plan_id not forwarded into execute_direct. The adapter overrode cmd_run to add the one-shot .pyprojectx cache-corruption self-heal retry but lost daemon routing in the process. FIX: re-thread daemon routing THROUGH the pyproject adapter so a registered-worktree pyproject build routes exactly like maven — route first (auto/daemon mode), record the requested-vs-resolved resolution line, then fall back to the in-process self-heal executor + build_queue_slot only when routing did not happen; forward plan_id/execution_mode/env_vars/working_dir intact so daemon_incompatible and execution_mode=daemon fail-loud match the other adapters. Mechanism is yours to choose at outline — the natural seam is to let the factory routing cmd_run call an overridable/injected in-process executor so pyproject supplies its self-heal wrapper as that executor, rather than duplicating the routing prefix — but pyproject MUST end up on the factory's single routing path with the self-heal intact on the in-process leg, with NO second copy of the routing/_record_resolution logic. The factory routing cmd_run is SHARED by maven/npm/gradle: any change to it must preserve their exact current behaviour (make it additive — an optional override defaulting to today's inner executor). Add regression tests asserting: (a) a registered-worktree auto-mode pyproject build ROUTES (submit boundary reached / resolved=routed) — impossible today; (b) the in-process fallback still fires the one-shot .pyprojectx self-heal retry on the documented corruption symptom; (c) a plan-less pyproject build runs unchanged (queue-slot NO-OP); (d) execution_mode=daemon with a daemon-incompatible env/working-dir fails loud like maven. Reuse PLAN-04 D5's execution_mode=in_process hermetic-declaration pattern to keep tests daemon-state-independent where needed. Add a doc note in doc/developer/build-architecture.adoc recording that pyproject now routes like the other adapters (cross-reference, not duplication). Cross-epic coordination: plan-optimization PLAN-32 touches sibling files _build_execute.py + manage-run-config/run_config.py in the same build-emit family; if you extend _build_execute_factory.py, watch for rebase adjacency and reuse rather than duplicate any shared seam. Full analysis and the verified root cause: .plan/local/orchestrator/plan-server/plans/PLAN-06-pyproject-routing-integration.md and .plan/local/orchestrator/plan-server/landings/PLAN-05.md"
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-06.md}
