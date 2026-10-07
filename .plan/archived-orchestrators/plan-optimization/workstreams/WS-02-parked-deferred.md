# WS-02: Parked / Deferred

epic: plan-optimization

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-02-parked-deferred.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Hold the follow-ups that are not startable as-is — parked pending re-scope, an operator
decision, or fresh data. Nothing here is emitted by `next` until it graduates (re-scoped at
outline, un-deferred by the operator, or promoted on recurrence). The workstream closes when
each item has either graduated into WS-01 (or a fresh epic) or been struck as obsolete.

## Scope

- In scope: the TT terminal-title stale `build-busy` spec (staged doc, but parked pending
  re-scope against BK #912's state-gate-first wake path); the `ci-pr-safe-merge` resume; the
  deferred consumer-repo `/marshall-steward upgrade` migrations.
- Out of scope: the four startable wave-2 plans (WS-01); the plan-server epic; the open §5
  defects still "held for data" that have no spec yet (they live in HANDOVER §5, promoted on
  recurrence).

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-05-terminal-title-stale-build-busy | ✅ shipped (PR #931) | REAL fix (not a no-op): `drop_stale_build_busy` on phase transition, scoped to build-busy. Left a stale merge-lock incident from the dead PLAN-06 dir |
| PLAN-06-ci-pr-safe-merge | ✅ shipped (PR #929) | Premise already-shipped (refine re-scoped) → 3 `configuration.adoc` doc rows. Both WS-02 plans done → WS-02 plan work COMPLETE (only deferred non-plan pointers remain) |

## Sequencing and Surface Notes

- **ci-pr-safe-merge (PLAN-06)** — was RESUME; the parked plan directory VANISHED (verified
  2026-07-18: not active, not orphaned, not archived — refine/outline state never persisted to this
  checkout or later removed). Converted to a FRESH init: settled design persisted in
  `plans/PLAN-06-ci-pr-safe-merge.md`, hand-off is `action=init` seeded from that spec. Merge-queue
  surface (#869/#897); org-wide bypass still deferred→steward.
- **Consumer migrations** — DEFERRED by operator (2026-07-16). `upgrade-regen-safety` #908
  un-gated them. Run `/marshall-steward upgrade` from inside each consumer, one at a time:
  API-Sheriff first (sharpest acceptance test — Leg B bricked it), then cui-jsf-test-basic,
  TokenSheriff, nifi. Steward action, not a plan spec.
- **PLAN-05 (TT)** — surface is `title_token=build-busy` plan-scoped state with no
  phase-transition reset. Promote to startable only after the re-scope confirms the defect
  still exists post-BK-#912.
