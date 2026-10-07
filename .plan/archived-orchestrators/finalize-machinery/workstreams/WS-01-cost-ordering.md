# WS-01: Finalize cost and step ordering

epic: finalize-machinery

> Charter document for one workstream — a coherent slice of the epic with its own goal
> and surface. Lives at `workstreams/WS-01-cost-ordering.md` and is tracked in the epic
> `status.json` `workstreams[]` field. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

Owns the finalize cost mechanism: a HEAD move inside finalize re-arms every head-bound
step, so the quality gate fires repeatedly for one tree and finalize outspends execute
3–5x. The outcome that closes it is a finalize pass whose head-bound steps certify the
tree review actually sees, with the re-fire loop retired or bounded.

## Scope

- In scope: phase-6-finalize step ordering and currency (pre-push-quality-gate,
  finalize-step-simplify, verdict_currency, ci_verify head anchoring, required-steps
  order), cost measurement of the re-fire loop
- Out of scope: invocation-surface wording (WS-02), merge-gate bot currency (WS-03),
  ledger/lessons pipeline and anchors (WS-04)

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-01-head-rearm | staged | Bind head-bound steps to one anchor so a mid-pass HEAD move cannot re-arm them |

## Sequencing and Surface Notes

- PLAN-01 runs first in effect: it is the highest-value target and its ordering
  decision constrains WS-03's gate work (a gate that certifies the wrong tree cannot be
  fixed by bot-currency alone).
- Surface adjacency with PLAN-04 (both touch phase-6-finalize standards, different
  files: ordering vs branch-cleanup) — sequence, do not parallelize, until PLAN-01 lands.
