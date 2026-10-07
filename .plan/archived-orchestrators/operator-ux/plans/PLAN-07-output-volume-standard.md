# PLAN-07: Bound user-facing output volume

epic: operator-ux
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-07-output-volume-standard.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
> See `persona-plan-orchestrator/standards/orchestration-model.md` for the tier and
> hand-off contract.

## Objective

plan-marshall emits far more text than a user needs to make the next decision. A strict bound
already exists on the sub-agent return path — one TOON block, `display_detail` ≤80 characters,
no narration — but that governs agent-to-orchestrator traffic, not orchestrator-to-user
traffic, which is what the user actually reads. Establish the missing rule: what the main
context prints to the user at a phase boundary is bounded by what the next decision needs.
The rule must distinguish two things that look alike and are not: **narration**, which is cut,
and **completeness of a reported outcome**, which is kept — a rule that trims the second
produces silent failures, a strictly worse defect than the one being fixed.

## Deliverables

1. The output-volume rule appended to `standards/user-communication.md` — the dedicated
   user-communication home PLAN-06 creates, joining the language and vocabulary rules so all
   three sit in one document. Scoped explicitly to main-context user-facing reporting, and
   explicitly NOT to sub-agent returns (already governed) or to authored documentation.
2. The narration/outcome distinction stated as the rule's central discrimination, with worked
   examples of each — including the case that motivates it: a failed step, a skipped step, and
   a partial result are outcome and must survive any trim.
3. A per-phase-boundary shape: what a user is owed when a phase completes (what changed, what
   is next, what needs them), and what is available on request rather than by default.
4. A cross-reference from `citations-only-return.md` naming this rule as the sibling that
   governs the other direction, so a reader of either finds the boundary between them.
5. The rule cites PLAN-06's vocabulary glossary rather than restating it — brevity in the
   system's own nouns is not brevity.

## Claim Labels

- OBSERVED: The sub-agent return path is bounded — "exactly one TOON block and nothing else",
  `display_detail` ≤80 chars, no prose preamble or closing summary — read at
  `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/citations-only-return.md`.
- OBSERVED: `standards/user-communication.md` is created by PLAN-06 and is this rule's home;
  it does not exist at HEAD. This plan APPENDS to it and does not create it — if PLAN-06 has
  not landed, this plan halts rather than creating a second home for the same concern.
- HYPOTHESIS: No equivalent bound governs main-context user-facing output. Asserted as an
  ABSENCE and to be verified as one — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/agent-behavior-rules.md`
  § the user-interaction / reporting rules, and by sweeping
  `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/` for a
  main-context output rule (verify-at-outline). ⛔ If such a rule exists, this plan re-scopes
  from "author" to "strengthen and enforce", which is materially smaller.
- HYPOTHESIS: The phase skills' user-facing report shapes are specified per phase rather than
  centrally, so a central rule is additive rather than conflicting — confirm/refute at
  `marketplace/bundles/plan-marshall/skills/phase-5-execute/SKILL.md` and
  `marketplace/bundles/plan-marshall/skills/phase-6-finalize/SKILL.md` § their user-facing
  reporting sections (verify-at-outline).
- Verify-first clause: the rule must not be authored in a way that a conforming agent can
  satisfy by omitting a failure. Settle the completeness floor — failures, skips and partial
  results are never trimmable — before the brevity ceiling is written, and state the floor
  first in the document so a reader meets it first.

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/standards/user-communication.md`
  — appended to; created by PLAN-06
- OBSERVED: `marketplace/bundles/plan-marshall/skills/ref-workflow-architecture/standards/citations-only-return.md`

## Dependencies and Sequencing

- Depends on: **PLAN-06** — hard. PLAN-06 CREATES `standards/user-communication.md`; this plan
  appends to it, and the volume rule refers to the vocabulary rule.
- Overlaps with: PLAN-06 (`standards/user-communication.md`) — hard sequence.
- No longer touches `agent-behavior-rules.md` or the persona `SKILL.md`: the load step and the
  pointer are PLAN-06's deliverables, so this plan's surface narrowed when the placement was
  settled.
- Adjacent to: the phase skills' own report shapes, read to verify the additivity claim and
  deliberately not edited here; applying the rule at those sites is PLAN-08's work.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/operator-ux/plans/PLAN-07-output-volume-standard.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message. The inbox exception's qualifiers and the
sole sanctioned write mechanism are stated in
`persona-plan-orchestrator/standards/orchestration-model.md` § Ledger Write-Boundary.
