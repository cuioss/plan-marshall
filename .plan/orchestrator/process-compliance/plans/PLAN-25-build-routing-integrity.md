# PLAN-25: Routed-build isolation, budget provenance and attribution

> ✅ **Staged 2026-09-29 under the standing operator directive ("issues about current problems are to be fixed,
> not relayed to PM-MCP").** Emittable; NOT subject to the PM-MCP parking of 2026-09-26.

epic: process-compliance
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-25-build-routing-integrity.md` and is queued in the epic's `queue/`
> row files. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.

## Objective

Make a routed build's verdict describe the build and not the infrastructure around it. In the PLAN-12 run:
- two whole-tree pytest runs routed to marshalld overlapped on one worktree and destroyed each other's
  basetemp, and the collision read as a genuine test red;
- a whole-tree `verify` was killed at 783 s against a learned budget of 1434 s, and nothing named the
  budget's source;
- every gate build reported `plan=NO_PLAN`.

## Deliverables

1. **Same-worktree runs cannot collide, and a collision is not a test red.** A whole-tree `module-tests` and a
   whole-tree `verify` were both `serialization=daemon-scheduled` yet ran overlapping. `module-tests` returned
   `status: error` with 10 `FileNotFoundError`s, all inside `.plan/temp/pytest-basetemp/<run>/popen-gwN`,
   while `verify` over the identical tree was green (28,188 tests). Either serialize runs against the
   same worktree, as the label implies, or give each run a private basetemp root. Classify a
   basetemp-vanished `FileNotFoundError` cluster as `indeterminate`, not `error`, so that
   pre-push-quality-gate Branch B and verification-feedback are not dispatched against non-defects.
2. **A build result names its budget and where it came from.** A routed whole-tree `verify` (`resolved=routed`,
   `mechanism=daemon_longpoll`) returned `status: timeout, timeout_used_seconds: 784`. The daemon's job log
   shows `./pw verify` itself was stopped at 783 s, while `run_config timeout measured --command
   python:verify` reports `measured: true, timeout_seconds: 1434`. Whole-tree verifies on the branch took
   917–1078 s, and an identical re-run finished green in 994 s. Echo `timeout_source` (learned / default /
   explicit) and the command key in the result TOON, and establish why this job received 783 s.
3. **Gate builds are attributed to their plan.** Every build the pre-push gate invoked reported
   `[BUILD-SERVER] ... plan=NO_PLAN`: the architecture-resolved executables carry no `--plan-id`, so the
   daemon attributes the plan's own gate builds to no plan. Forward the plan identity.

**Re-scoped at cleanup 2026-09-29 (HEAD `56add3f`):**
- **D1:** each run already gets its own pid-uuid basetemp (`build.py _prepare_session_basetemp`
  :264-291). The collision comes from the cross-session prune: `_prune_basetemp_roots` (:233-261) keeps
  only the newest dir and `rmtree`s a concurrent live older session's root (`:245-246` names the
  `popen-gwN` symptom). D1 is prune retention (never remove a live session's root) and/or scheduler
  serialization per worktree (`admit_next` :202-223 checks only the global slot). The
  `indeterminate` classification half is unchanged.

## Claim Labels

- OBSERVED: overlapping routed runs, 10 basetemp `FileNotFoundError`s vs green `verify` (28,188 tests) — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-015.md`
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _marshalld_scheduler.admit_next:202-223 global slot only, no same-worktree exclusion; build.py _prune_basetemp_roots:233-261 rmtrees non-newest session dirs (:245-246 popen-gwN)
- OBSERVED: killed at 783 s vs learned 1434 s; re-run green in 994 s — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-031.md`
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: no timeout_source/command_key in any result TOON (_build_result.py 0 hits); marshalld _DEFAULT_JOB_TIMEOUT=1800 (:73) so 783s came from the child's resolution
- OBSERVED: `plan=NO_PLAN` on every gate build — cited at `inbox/archive/plan-12-tool-triage/plan-12-tool-triage-027.md` § Also observed
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _build_execute_factory cmd_run:1091 plan_id=args.plan_id; resolved executables carry no --plan-id (pre-push-quality-gate.md:342) -> routing_plan_id=NO_PLAN (:760)
- HYPOTHESIS: the per-session basetemp root is created by `build.py` (`pyproject.toml:302-304` comment at HEAD) — confirm/refute at `build.py` § the `--basetemp` construction (verify-at-outline)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: build.py:114-121 PYTEST_BASETEMP_ROOT; _prepare_session_basetemp:264-291 per-run pid-uuid dir (--basetemp :817-823)
- HYPOTHESIS: same-worktree serialization is decided in `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_scheduler.py` — confirm/refute at that file § the job admission / slot logic (verify-at-outline)
  - verdict: corroborated | checked_at: 56add3fafe362e058a8e1b5d4608ac34ec77196b | by: process-compliance/cleanup | rescoped: n/a | evidence: _marshalld_scheduler.py admit_next:202-223 slot count + round-robin only; submit:181-183 dedups identical fingerprint; no worktree serialization

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_scheduler.py` — same-worktree serialization
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/marshalld.py` — job budget, result echo
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute.py` — routed execution, plan attribution
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_result.py` — `timeout_used_seconds`, indeterminate classification
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_shared.py` — result shaping
- OBSERVED: `build.py` — per-run basetemp root
- OBSERVED: `test/plan-marshall/build-server/`
- OBSERVED: `test/plan-marshall/script-shared/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_execute_factory.py` — `_record_resolution` plan attribution, `_route_to_daemon` (D2, D3) (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/script-shared/scripts/build/_build_cli.py` — `run` subparser `--plan-id` / `NO_PLAN` default (D3) (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-architecture/scripts/_cmd_client_build.py` — resolved executable has no `--plan-id` (D3) (added cleanup 2026-09-29 at 56add3f — understated surface)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-build-server/scripts/_marshalld_supervisor.py` — child budget (D2) (added cleanup 2026-09-29 at 56add3f — understated surface)

## Dependencies and Sequencing

- Depends on: none
- Overlaps with: PLAN-19 (`_build_shared.py`, D2 double finding persistence) and PLAN-23 (build-server-client wait bound). Sequence after PLAN-19; check against PLAN-23.
- Scope-bloat guard: 3 deliverables.

## Folded inbox material (same act)

- `plan-12-tool-triage-015.md` (finding): deliverable 1
- `plan-12-tool-triage-031.md` (finding): deliverable 2
- `plan-12-tool-triage-027.md` (finding) § Also observed: deliverable 3

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-25-build-routing-integrity.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
