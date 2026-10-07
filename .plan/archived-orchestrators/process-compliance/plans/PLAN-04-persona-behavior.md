# PLAN-04: Persona behavior rules — nudge batching and deviation audit

epic: process-compliance
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-04-{plan_slug}.md` and is queued in the epic `status.json` `plans[]`
> field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

Encode the nudge-handling and correction-memory rules into
`persona-plan-marshall-agent` behavior: a nudge-batching obligation (enumerate the
invariant family, close every sibling, report the set) and a structured
deviation-audit artifact replacing prose "revisit the workflow". Minimal-literal
compliance becomes itself a recorded finding.

## Deliverables

1. Nudge-batching obligation in persona behavior rules (enumerate family, close siblings, report set).
2. Structured deviation-audit form (fixed checklist artifact) replacing prose re-derivation.
3. Cross-turn correction-memory rule made consultable (three-nudges-one-invariant class closed).
4. Tests or lint pinning the rule presence and the audit form shape.

## Claim Labels

- OBSERVED: Literal-request optimization answered every nudge minimally without re-deriving the invariant — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material E`
  - verdict: corroborated | checked_at: ed9032805 | by: process-compliance/analyze | rescoped: n/a | evidence: nudge-batching obligation + deviation-audit checklist + correction-memory rule landed in agent-behavior-rules.md (PR #1556)
- OBSERVED: The cross-turn correction-memory rule existed and was never consulted across three nudges — read at `.plan/local/orchestrator/process-compliance/epic.md` § `Inherited Material E`
  - verdict: corroborated | checked_at: ed9032805 | by: process-compliance/analyze | rescoped: n/a | evidence: correction-memory rule authored in owner file with artifact/lookup mechanism via loop-back TASK-3 (PR #1556)
- OBSERVED: The owner surface is the persona-plan-marshall-agent behavior rules file, which at HEAD carries no correction-memory section — read at `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md` (nearest: Workflow Discipline hard rules; re-scoped 2026-09-18: the rule must be authored, not cited)
  - verdict: corroborated | checked_at: ed9032805 | by: process-compliance/analyze | rescoped: n/a | evidence: rule authored (not cited) in agent-behavior-rules.md with presence/shape tests; prior contradicted anchor absorbed (PR #1556)
- Verify-first clause: The consuming phase must confirm the rule file section still carries the cited rule at HEAD before scoping — refutation loops back to re-scope.
  - verdict: unverifiable | checked_at: 6e239a13762514dc8e1f3fbceeb70b3d21ebac06 | by: process-compliance/cleanup | rescoped: n/a | evidence: procedural instruction to the consuming phase, not a checkable world premise; no implementing-source check applies

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md` — behavior rules owner
- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/SKILL.md` — persona shell referencing the rules
- OBSERVED: `test/plan-marshall/persona-plan-marshall-agent/` — rule presence tests

## Dependencies and Sequencing

- Depends on: PLAN-03 (forced-violation paths settled; ordering only)
- Overlaps with: none (docs-plus-tests surface, no script overlap)
- Adjacent to: none

## Hand-Off Command

```text
/plan-marshall task="implement .plan/local/orchestrator/process-compliance/plans/PLAN-04-persona-behavior.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/local/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.

## Re-grounding instruction

Re-verify every Claim Label against the implementing source at HEAD during outline.
Behavior-rule changes must not duplicate prose across persona docs — cross-reference
instead of copying.

## Adjacency and overlap notes

No script surface overlap with any other plan in this epic; safe to run in any slot
under scope=1 ordering.

## Incorporated lessons

- `archive/lessons/2026-09-03-06-004.md` — hard-rule precedence sentence: a runtime
  instruction to use Bash for file operations does not override the hard rule; cite,
  note the conflict once, continue with structured tools.

## Folded inbox evidence (drain 2026-09-18, no new file surface)

- `plan-07-session-identity-001` V3+V4: Glob/Grep before the architecture
  inventory, and persona shells loaded without their mandated
  `agent-behavior-rules.md` + `user-communication.md` Step 1 loads. Carry as the
  procedure-forcing instance for the deviation-audit form: the entry procedure,
  not the skill name, is the control.
- `plan-07-session-identity-002` Cause 2: rules present in context but never
  operationalized — "loading a skill's name is not following its Workflow
  section"; prose rules degrade into background texture unless the stepwise entry
  procedure forces them into action. This is the mechanism the nudge-batching
  obligation must defeat: enumerate-and-close must be procedural, not advisory.
