# PLAN-NN: {Plan Title}

epic: {slug}
workstream: WS-NN

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

{2-4 sentences: what this plan ships and why, phrased so it can be pasted as the
/plan-marshall request narrative.}

## Deliverables

{Enumerate the expected deliverables. A spec approaching ~6 deliverables is
presumptively split before its command is emitted — record the split-or-proceed
rationale as an epic decision.}

1. {deliverable}
2. {deliverable}

## Expected Surface

{Files/modules this plan is expected to touch — the input to the surface-disjointness
check before this plan may run concurrently with another.}

- {path or module}

## Dependencies and Sequencing

{Plans that must land first, and known overlaps that force sequencing.}

- Depends on: {PLAN-NN or none}
- Overlaps with: {PLAN-NN surfaces or none}

## Hand-Off Command

{The ready-to-run command the orchestrator emits when this plan reaches the queue head.
Fill the request text from the Objective and Deliverables above.}

```text
/plan-marshall {request text}
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` — the orchestrator owns every ledger write
— and reports its outcome through its PR alone. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
