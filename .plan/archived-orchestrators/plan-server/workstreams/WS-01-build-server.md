# WS-01: Build server (`marshalld`)

epic: plan-server

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-build-server.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Build the machine-level daemon (`marshalld`) that owns build-class work — builds and test runs — on
behalf of every plan-marshall session on the machine, so a harness-reaped session `wait` re-polls a
surviving job instead of destroying it, and cross-project builds share one CPU-fair queue. Rung 1
(`plan-global-home-root`, PR #923) shipped the `~/.plan-marshall/` machine-global home the daemon
needs; this workstream is Rung 2 — the server itself, its client/control skills, the init preflight
gate, and the as-built docs. The workstream closes when the daemon ships, a registered project's
builds survive a wait reap, and the docs land.

## Scope

- **In scope:** the `marshalld` daemon (asyncio subprocess supervisor, Unix socket, double-fork
  daemonization); the tiny `build-server-client` consumption skill; the `manage-build-server` control
  skill (install/upgrade/start/stop/drain/status/register/unregister); `phase-1-init` preflight gate
  (registry read + ping + ask-to-start); the queue surface (`build_queue.py` subsume/retire);
  `await-long-running.md` seam replacement; the security model S1–S9 (verify-not-resolve,
  clean-baseline env, socket identity handshake, credentials adjacency); the documentation surface
  (README + installation WSL2 requirement, `doc/concepts/build-server.adoc`, `doc/developer/
  build-architecture.adoc`, concept-doc xrefs).
- **Out of scope:** CI-waiting (fails the scope criterion — stays on bounded `ci:wait` primitives);
  any wake/dormancy mechanism (settled non-goal); token/finalize-idle savings framing (off-thesis);
  Rung 1 (already shipped); the optional MCP facade (record-only, additive-later).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-plan-server-core | shipped | Rung 2 daemon + client/control skills + init preflight + S1–S9 + docs 1–6. Shipped PR #933 (07-18). Landing: `landings/PLAN-01.md`. |
| PLAN-02-registration-scope-population | staged | Post-ship defect fix: register/enable path writes empty scope → daemon inert. Reopened 07-19. Spec: `plans/PLAN-02-registration-scope-population.md`. |
| PLAN-03-interaction-audit-logging | staged | Client work-log + server-side audit log + correlation; each interaction auditable. Sequenced after PLAN-02 (shared surface). Spec: `plans/PLAN-03-interaction-audit-logging.md`. |

## Sequencing and Surface Notes

- Single-plan workstream: the daemon, client skill, control skill, queue, and init gate are
  surface-interlocked (daemon ↔ `build_queue.py` ↔ client seam ↔ `phase-1-init`) and cannot ship
  independently — they are one tightly-coupled unit whose internal decomposition is the plan's own
  DESIGN-FIRST outline's job, not an orchestrator-level split. Scope-bloat guard evaluated and
  overridden with rationale (epic Decisions, 2026-07-17).
- No concurrent plan to check disjointness against — WS-01 is the only active workstream and Rung 1
  is closed.
- At outline: re-read the shipped Rung 1 surface (post-#923, not the spec's pre-#923 line refs) and
  verify the `plan_id=null` build-queue bypass is closed; fold in the inherited worktree-resolution
  defects (epic Open Defects) if they touch the queue/registration path.
