# PLAN-NN: {Plan Title}

epic: {slug}
workstream: WS-NN

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
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

## Claim Labels

{Every claim this spec serializes is labelled `OBSERVED` or `HYPOTHESIS` per
`persona-marshall-orchestrator/standards/orchestration-model.md` § Verify-First Contract for
Inferred Claims. Label all three classes: the inferred mechanism, the Expected Surface below,
and every derived count or sharpened finding. A HYPOTHESIS names the file plus symbol that
confirms or refutes it and is marked verify-at-outline. An asserted absence is labelled and
verified exactly like an asserted presence.}

- OBSERVED: {claim} — read at `{file}` § `{symbol}`
- HYPOTHESIS: {claim} — confirm/refute at `{file}` § `{symbol}` (verify-at-outline)
- Verify-first clause: {anything the consuming phase must settle against the implementing
  source before it may scope — refutation loops back to re-scope}

## Expected Surface

{Files/modules this plan is expected to touch — the input to the surface-disjointness
check before this plan may run concurrently with another. Label each entry per Claim Labels
above, and re-verify the whole surface against HEAD at outline before scoping on it.}

- {path or module}

## Dependencies and Sequencing

{Plans that must land first, known overlaps that force sequencing, and adjacency notes —
surfaces this plan sits next to without touching, which a reader needs to avoid re-deriving.}

- Depends on: {PLAN-NN or none}
- Overlaps with: {PLAN-NN surfaces or none}
- Adjacent to: {nearby surface and why it stays untouched, or none}

## Hand-Off Command

{The ready-to-run command the orchestrator emits when this plan reaches the queue head. The
command is a ONE-LINE POINTER to this spec path — the spec body is the brief, so nothing is
transcribed into the command.}

```text
/plan-marshall Execute the staged plan spec at .plan/local/orchestrator/{slug}/plans/PLAN-NN-{plan_slug}.md
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` — the orchestrator owns every ledger write
— and reports its outcome through its PR alone. See
`persona-marshall-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
