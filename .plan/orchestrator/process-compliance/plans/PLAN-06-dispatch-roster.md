# PLAN-06: Dispatch roster and producer vocabulary

epic: process-compliance
workstream: WS-05

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-06-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Close the remaining two dispatch-contract lessons: enforce the producer vocabulary
consistently (`ci-verify-timeout` accepted once, contract-violated once) and carry
each step's prompt skills in the dispatch roster, pinned by the roster-closure test
family. Lands on top of PLAN-05's settled envelope shapes.

## Deliverables

1. Producer vocabulary consistently enforced (single accept-set, tested both directions).
2. Dispatch roster carrying each step's prompt skills.
3. Roster-closure test family pinning the roster.
4. Docs naming the vocabulary and the roster contract (lesson evidence: 2026-09-17-19-007, -008).

## Claim Labels

- OBSERVED: Producer vocabulary inconsistently enforced across two observations — read at `.plan/orchestrator/process-compliance/epic.md` § `Inherited Material F`
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic.md Inherited Material F unchanged since prior check; enforcement behavior still not checkable by file read; unchanged
- OBSERVED: Dispatch roster should carry each step's prompt skills — read at `.plan/orchestrator/process-compliance/epic.md` § `Inherited Material F`
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: epic.md Inherited Material F unchanged since prior check; gap premise still names no implementing symbol; unchanged
- HYPOTHESIS: The roster and vocabulary seams live beside the PLAN-05 dispatch paths — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md` § `Dispatched steps` (verify-at-outline; re-scoped 2026-09-18: not operations.md)
  - verdict: corroborated | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: dispatch-inline-split.md unchanged since 93bda90; Dispatched steps section still present at :13; re-confirmed
- Verify-first clause: The consuming phase must settle the HYPOTHESIS against the implementing source before scoping — refutation loops back to re-scope.
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-6-finalize/standards/dispatch-inline-split.md` — dispatch/inline roster owning prompt-skill columns
- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-5-execute/standards/operations.md` — roster-adjacent dispatch docs
- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/execute-task/scripts/inject_project_dir.py` — roster consumer seam (verify-at-outline)
- OBSERVED: `test/plan-marshall/phase-5-execute/` — roster-closure tests

## Dependencies and Sequencing

- Depends on: PLAN-05 (envelope shapes settled first — hard sequence, same family)
- Overlaps with: PLAN-05 (same dispatch family — sequence, do not parallelize); PLAN-13 (`dispatch-inline-split.md`, discovered when PLAN-13 was staged — confirmed via `corpus cross-check` — sequence, do not parallelize)
- Adjacent to: none

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-06-dispatch-roster.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Re-grounding instruction

Re-verify every Claim Label against the implementing source at HEAD during outline;
settle the HYPOTHESIS via `corpus set-verdict` before scoping. Ground each contract in
the cited corpus lesson evidence (007/008).

## Adjacency and overlap notes

If PLAN-05 reshaped the dispatch paths, re-ground this spec's surface against the new
HEAD before scoping — do not scope against pre-PLAN-05 paths.

## Incorporated lessons

- `archive/lessons/2026-09-17-19-007.md` — producer vocabulary: accept
  `ci-verify-timeout` as a routed alias or reject consistently with a named owner.
- `archive/lessons/2026-09-17-19-008.md` — dispatch roster carries each step's prompt
  skills, pinned by the roster-closure test family.

## Folded inbox evidence (drain 2026-09-18, no new file surface)

- `git-branch-mechanics-001` item 7: `plan-retrospective` leaf returned success
  with no `mark-step-done`, tripping `assert-step-recorded` (backfilled by hand).
  Carry a dispatcher-side completion guard for this roster entry into the roster
  deliverable — a silent success with no record is the gap `record-before-return`
  exists to close.
turn`
  exists to close.
