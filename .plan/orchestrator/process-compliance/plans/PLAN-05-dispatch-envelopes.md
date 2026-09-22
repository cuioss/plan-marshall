# PLAN-05: Dispatch envelope contracts

epic: process-compliance
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-05-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Close the three dispatch-envelope gaps from plan-03-review-currency: generic dispatch
must defer to step-owned dispatch bodies (`requires_prompt_fields`, author/verifier
choreography); the fix-task loop-back dispatch shape must state its envelope fields;
and `loop_back_target` must be present on verification-feedback loop_back returns.
Each gap gets a contract plus a closure test.

## Deliverables

1. Step-owned dispatch body contract (`requires_prompt_fields`, author/verifier choreography) with generic-dispatch deferral.
2. Fix-task loop-back dispatch shape with stated envelope fields.
3. `loop_back_target` required on verification-feedback loop_back returns.
4. Closure tests pinning each contract (lesson evidence: 2026-09-17-19-004, -005, -006).

## Claim Labels

- OBSERVED: Generic dispatch must defer to step-owned dispatch bodies — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material F`
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic.md Inherited Material F unchanged since prior check (git diff 93bda90..HEAD confirms epic.md not in changed set); ledger-cite premise still not re-opened; unchanged
- OBSERVED: Fix-task loop-back dispatch shape states no envelope fields — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material F`
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic.md Inherited Material F unchanged since prior check; ledger-cite premise still not re-opened; unchanged
- OBSERVED: `loop_back_target` is missing on verification-feedback loop_back returns — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material F`
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic.md Inherited Material F unchanged since prior check; ledger-cite premise still not re-opened; unchanged
- HYPOTHESIS: The dispatch registry seam lives under the execute-task / phase-5 dispatch paths — confirm/refute at `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py` § `inject_project_dir` (verify-at-outline; corrected 2026-09-18: full symbol, subcommand dispatch at :208)
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: inject_project_dir.py unchanged since 93bda90; inject_project_dir still defined at :82 with subcommand dispatch at :208; re-confirmed
- Verify-first clause: The consuming phase must settle the HYPOTHESIS against the implementing source before scoping — refutation loops back to re-scope.
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py` — dispatch seam (verify-at-outline)
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md` — dispatch body docs
- OBSERVED: `test/plan-marshall/phase-5-execute/` — dispatch contract tests

## Dependencies and Sequencing

- Depends on: PLAN-04 (persona rules settled; ordering only)
- Overlaps with: PLAN-06 (same WS-05 dispatch family — sequence, do not parallelize)
- Adjacent to: WS-03 invocation paths — contracts vs. paths, no overlap

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/process-compliance/plans/PLAN-05-dispatch-envelopes.md"
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
settle the HYPOTHESIS via `corpus set-verdict` before scoping. Ground each contract in
the cited corpus lesson evidence (004/005/006).

## Adjacency and overlap notes

PLAN-06 extends this work (producer vocab + roster skills) on the same dispatch
family: land PLAN-05 first so the roster pins settled shapes.

## Incorporated lessons

- `archive/lessons/2026-09-17-19-004.md` — generic dispatch defers to step-owned
  dispatch bodies (`requires_prompt_fields`, author/verifier choreography).
- `archive/lessons/2026-09-17-19-005.md` — fix-task loop-back dispatch shape (no
  envelope): state carried/omitted fields explicitly.
- `archive/lessons/2026-09-17-19-006.md` — `loop_back_target` required on every
  verification-feedback `loop_back` return.
- `archive/lessons/2026-09-03-07-001.md` — precursor: pre-flight prompt bodies
  against `requires_prompt_fields` at the dispatch site (130K-token round trip).

## Folded inbox evidence (drain 2026-09-18, no new file surface)

- `git-branch-mechanics-001` item 6: triage-created fix tasks (TASK-4..8) arrived
  with `envelope_id: null`, invisible to the envelope-filtered executor; operator
  hand-stamped `envelope_id: 1`. Live recurrence of archived -005: carry the
  null-envelope execution rule (re-run bin-packer at loop-back entry, or define
  the rule explicitly) into the loop-back dispatch-shape deliverable.
