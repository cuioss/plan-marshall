# PLAN-PR-075: The telemetry channels a finalize run reports itself through

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `superseded`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> [`findings/2026-09-26-pm-mcp-carry-over.md`](../findings/2026-09-26-pm-mcp-carry-over.md) as PM-MCP input.
> Do NOT emit. `superseded` is terminal; re-staging needs an explicit operator decision.

epic: review-apparatus
workstream: WS-04

> **Component-cut spec, authored 2026-09-18.** This plan owns ONE component: `manage-status` / `manage-metrics` / `manage-logging` — the step record, the token accumulator, and the `[VERIFY]` channel.
> ⛔ **Every deliverable body below lives in its ORIGINAL source spec and is NOT restated here** — the
> `Carried from` column names the theme spec this deliverable was cut out of, and that spec's own
> pointer names the retired spec holding the body. Follow the chain; do not retype.
>
> The theme specs `PLAN-PR-056` … `PLAN-PR-064` were retired on 2026-09-18 because their surfaces
> overlapped almost totally — `_findings_core.py` was declared by 7 of 9 — so no two could ever run
> concurrently. The cut is by component, so **no file is declared by two live plans**.

## Objective

Make a step record self-validating about the head it describes, and make a channel that produced nothing say so rather than reporting a settled total.

## Deliverables

| # | Deliverable | Body lives at | Carried from |
|---|---|---|---|
| D0 | Make a step record self-validating about its head | `PLAN-PR-050` § D1 | `PLAN-PR-063` D1 |
| D1 | Three channels go dark over `6-finalize`, and a green completeness flag does not cover it | `PLAN-PR-050` § D2a | `PLAN-PR-063` D3 |
| D2 | Resolve the `VERIFY` channel one way | `PLAN-PR-050` § D3 | `PLAN-PR-063` D4 |
| D3 | Record the open lifecycle choices as proposals, and give the foreign column a consumer | `PLAN-PR-028` § D6 | `PLAN-PR-064` D6 |


4 deliverables — within the guideline (12 nominal, ~14 when the aspects fit together, operator ruling 2026-09-15). ⛔ **Absorb nothing from another component**: the re-cut exists so this plan's surface stays disjoint.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/standards/status-lifecycle.md`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-metrics/`
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-logging/standards/log-format.md`
- OBSERVED: `test/plan-marshall/manage-status/`

## Claim Labels

- OBSERVED (2026-09-18): every deliverable in this plan was carried verbatim from the theme spec named
  in its `Carried from` column, which carries the claim labels for its own deliverables. Confirm/refute
  by reading that spec's `## Claim Labels` section — this plan re-states none of them.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: Structural carried-verbatim claim, verified by reading this spec at HEAD: four pointer deliverables, no restated body.
- OBSERVED (2026-09-18, orchestrator `corpus surfaces` + per-deliverable mapping): this plan's declared
  surface is disjoint from every other live plan's in this epic. Confirm/refute with
  `orchestrator corpus cross-check --slug review-apparatus`.
  - verdict: corroborated | checked_at: 7d82d5d90 | by: review-apparatus/cleanup | rescoped: n/a | evidence: DISJOINTNESS HOLDS and is the strongest in the corpus, derived by membership: manage-status, manage-metrics and manage-logging are declared by no other staged spec, exactly as this spec own Dependencies claims. But the surface MOVED heavily - _cmd_lifecycle.py (+334), _cmd_mark_step.py (+70), manage-status.py (+16), SKILL.md (+63), status-lifecycle.md (+7), manage-metrics and log-format.md all changed. Light method on the bodies: the surface is DISTURBED and every D0 coordinate must be re-derived at outline.


## Dependencies and Sequencing

- ⭐ **Disjoint from every other live plan** — `manage-status`, `manage-metrics` and `manage-logging`
  are declared by no other spec in this epic. This is the plan to pair with a WS-01/WS-03 plan.
- ⚠ D0 arm (b) (a `stale` verdict rather than dispatcher-enforced re-marking) changes the wording
  `PLAN-PR-071` D9 relies on. Whichever arm is taken, tell 071.
- ⚠ D3 carries only the CODE half of its source deliverable (the `manage-metrics` host/foreign split
  and its intent-bearing fixtures). Its three operator proposals were routed to orchestrator
  housekeeping at the re-cut and are not this plan's.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/review-apparatus/plans/PLAN-PR-075-the-telemetry-channels-of-finalize.md"
```

## Write-Boundary

The plan implementing this spec writes to its own repository source only. It creates and edits NO file
under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}` message.
