# PLAN-04: Live-client verification per entry kind, red-first

epic: model-provisioning
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-NN-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Prove the epic done-state with live clients: each dispatch level resolves to the user's configured model through the local map for both entry kinds (a local model and a provider-routed config such as Zen/Go), verified red-first, with the narrow-but-never-escalate posture enforced. Unpinned levels must still dispatch inherit-only.

## Deliverables

1. Red-first verification per entry kind: failing-before-passing evidence that each level resolves to the configured local model and to the configured provider entry.
2. Fallback check: unpinned levels dispatch inherit-only (session model), proving the workaround-turned-fallback survived.
3. Narrow-but-never-escalate posture check: no resolution exceeds its configured level under either entry kind.
4. Landing evidence recorded for the epic close-out.

## Claim Labels

- OBSERVED: The epic done-state is each dispatch level resolving to the user's configured model (local or provider) with narrow-but-never-escalate enforced and verified red-first — read at `.plan/orchestrator/model-provisioning/epic.md` § `Vision`
- OBSERVED: The epic sequences schema plus resolve-chain slot first, the steward step second, and live-client verification per entry kind third — read at `.plan/orchestrator/model-provisioning/epic.md` § `Provenance and sequencing`
- OBSERVED: Execution-context dispatches pin model and effort by which level variant is dispatched, via the Task prompt body contract — read at `marketplace/bundles/plan-marshall/agents/execution-context.md` § `Input — Prompt-Body Contract`
- HYPOTHESIS: A live OpenCode session can observe per-level model resolution distinctly for a local-model pin and a provider-config pin — confirm/refute at `marketplace/targets/opencode/emitter.py` § `emit_bundles` (verify-at-outline)
  - verdict: unverifiable | checked_at: fb8aadc9 | by: model-provisioning/cleanup | rescoped: n/a | evidence: no pin mechanism exists at this sha (PLAN-02/03 unbuilt), so per-kind live observability cannot be checked; settling is PLAN-04 outline against the built surface
- Verify-first clause: The consuming outline phase must settle the HYPOTHESIS against the emit implementing source and the live harness before scoping the verification matrix — refutation re-scopes what can be observed live.

## Expected Surface

- OBSERVED: `test/marketplace/targets/opencode/test_variant_emitter.py` — emitter verification tests to extend
- OBSERVED: `test/marketplace/targets/opencode/test_level_table_lockstep.py` — lockstep tests adjacent to the change
- OBSERVED: `test/plan-marshall/marshall-steward/test_effort_menu.py` — steward effort tests adjacent to pin behavior

## Dependencies and Sequencing

- Depends on: PLAN-02-steward-pin-materialization, PLAN-03-emitter-reenable (both must land first)
- Overlaps with: none
- Adjacent to: implementation surfaces (read-only here; this plan writes verification only)

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/model-provisioning/plans/PLAN-04-live-verification.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
