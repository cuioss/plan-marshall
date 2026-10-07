# PLAN-01: Phase-completion artifact gates

epic: process-compliance
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-01-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Enforce phase-completion artifact gates inside `manage-status transition` so bare
2-refine/3-outline/4-plan transitions are refused unless the phase artifact exists,
with an explicit logged exemption for legitimately artifact-free phases. This is the
highest-leverage structural guard in the epic: the deviation is decidable at the
transition boundary itself.

## Deliverables

1. Transition gate: refuse `--completed 3-outline` unless solution_outline.md validates; refuse `--completed 4-plan` unless ≥1 task file exists or the manifest is composed; refuse `--completed 2-refine` unless the clarified/confidence record exists.
2. Exemption metadata: explicit, decision-logged exemption for legitimately artifact-free phases, visible to retrospectives.
3. Regression tests pinning each refusal and each exemption path.
4. Docs update naming the gate and the exemption form.

## Claim Labels

- OBSERVED: Bare 2-refine/3-outline/4-plan transitions with zero artifacts are decidable inside manage-status transition and nothing checks — read at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` § `manage-status`
  - verdict: corroborated | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: cmd_transition guards are drift/verify/handshake based; no solution-outline, task-file, or clarify artifact predicate anywhere in manage-status/scripts
- OBSERVED: Authoring a fix does not immunize the authoring (corpus lesson 2026-09-06-08-001) — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material B`
  - verdict: corroborated | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic Inherited Material B cites 2026-09-06-08-001; verbatim copy verified at archive/lessons/2026-09-06-08-001.md
- HYPOTHESIS: The transition command routes through `_cmd_lifecycle.py` where the gate belongs — confirm/refute at `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` § `cmd_transition` (verify-at-outline)
  - verdict: corroborated | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: cmd_transition defined at _cmd_lifecycle.py:393 with transition-side completion guards and drift refusal
- Verify-first clause: The consuming phase must settle the HYPOTHESIS against the implementing source before scoping — refutation loops back to re-scope. Must not soften the fail-closed boundary guards (epic § H).
  - verdict: unverifiable | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/manage-status.py` — transition entry point
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_cmd_lifecycle.py` — presumed transition implementation
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/manage-status/scripts/_status_core.py` — status read/write core the gate reuses (verify-at-outline)
- OBSERVED: `test/plan-marshall/manage-status/` — regression tests for the gate

## Dependencies and Sequencing

- Depends on: none (first in queue)
- Overlaps with: none (only plan touching manage-status)
- Adjacent to: WS-02 phase-boundary assertions — adjacent boundary, separate files, no touch

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/process-compliance/plans/PLAN-01-phase-gates.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Re-grounding instruction

Re-verify every Claim Label against the implementing source at HEAD during outline;
settle each HYPOTHESIS via `corpus set-verdict` before scoping. Do not proceed on a
refuted premise.

## Adjacency and overlap notes

WS-01 also reasons about phase boundaries but owns `prepare_execute`/phase-5 dispatch,
never `manage-status transition`. If the gate needs a shared validator, duplicate the
small check rather than importing across the boundary.

## Incorporated lessons

- `archive/lessons/2026-09-06-08-001.md` — subject-class self-review pass: the gate
  authoring must itself be reviewed against the artifact-gate class it enforces.
