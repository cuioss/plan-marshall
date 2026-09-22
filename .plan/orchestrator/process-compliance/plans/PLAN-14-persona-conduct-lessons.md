# PLAN-14: Persona-agent conduct lessons

epic: process-compliance
workstream: WS-04

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-14-persona-conduct-lessons.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline. This spec is SELF-SUFFICIENT: the emitted command is a
> one-line pointer and carries no brief, so every per-plan carry is authored here and
> nowhere else.

## Objective

Close five recurring `persona-plan-marshall-agent` conduct gaps surfaced since PLAN-04
shipped: argparse rejections recurring despite the executor already naming the fix, a
fix landing on the wrong population unit, only/all/none/the-set-is-N claims missing
their enumeration and scope, a closed-vocabulary escape hatch assigning the out-of-scope
case a set member instead of placing it outside the set, and re-derived coverage figures
producing structurally impossible zeros. Each gap gets a stated rule plus a closure test
on the foundational agent behavior surface.

## Deliverables

1. Argparse-rejection recurrence rule: when the executor's error already names the fix,
   the agent MUST apply it before retrying — no re-attempt of the same rejected call
   shape. Ground in the primary lesson's tally (20 script failures, 12 unique, dominant
   class argparse rejection not script-internal error).
2. Fix-scope rule: a fix's unit is the derived co-reference population, never only the
   site a finding named — state the rule and add a closure test that a fix touching one
   site of a multi-site population is flagged incomplete.
3. Enumeration-with-claim rule: every only/all/none/the-set-is-N claim MUST carry the
   enumeration and the scope it was derived over — no bare cardinality claim.
4. Closed-vocabulary escape-hatch rule: an out-of-scope case is placed OUTSIDE the
   vocabulary's set, never assigned a set member as a stand-in.
5. Coverage-figure integrity rule: a coverage figure re-derived in transit (summarized,
   re-aggregated, passed through a second computation) MUST NOT silently produce a
   structurally impossible zero — the re-derivation is checked against the population it
   claims to cover.

(5 deliverables, one shared-component cluster per the source drain's own grouping —
kept unsplit under the Scope-Bloat Split Guard because all five are conduct rules on the
same `persona-plan-marshall-agent` foundational surface and share one verification pass;
none touches a second file surface independently.)

## Claim Labels

- OBSERVED: argparse rejections recur across scripts despite the executor already naming
  the fix — one plan recorded 20 script failures, 12 unique, dominant class argparse
  rejection not script-internal error — read at
  `.plan/orchestrator/process-compliance/inbox/lessons-handling-26-09-22-01-001.md`
  § Persona-plan-marshall-agent foundational conduct (lesson 2026-09-21-10-001, primary)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: ledger cite (lessons-handling drain message); the cited plan's 20/12 tally not re-opened this pass
- OBSERVED: a fix's unit is the derived co-reference population, never the site the
  finding named — read at same message § Persona-plan-marshall-agent foundational conduct
  (lesson 2026-09-19-21-003)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: ledger cite (lessons-handling drain message); not opened this pass
- OBSERVED: every only/all/none/the-set-is-N claim carries the enumeration and the scope
  it was derived over — read at same message § Persona-plan-marshall-agent foundational
  conduct (lesson 2026-09-19-21-004)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: ledger cite (lessons-handling drain message); not opened this pass
- OBSERVED: a closed-vocabulary rule's escape hatch must place the out-of-scope case
  OUTSIDE the set, not assign it a set member — read at same message §
  Persona-plan-marshall-agent foundational conduct (lesson 2026-09-20-08-012)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: ledger cite (lessons-handling drain message); not opened this pass
- OBSERVED: coverage figures re-derived in transit produce structurally impossible zeros
  — read at same message § Persona-plan-marshall-agent foundational conduct (lesson
  2026-09-21-10-004)
  - verdict: unverifiable | checked_at: 7d82d5d906c62312c708ac8993dc5f8f4d46bfa6 | by: process-compliance/analyze | rescoped: n/a | evidence: ledger cite (lessons-handling drain message); not opened this pass
- HYPOTHESIS: the foundational conduct rules governing all five lessons live in
  `persona-plan-marshall-agent`'s own standard, the single base every persona inherits —
  confirm/refute at
  `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/` § conduct rules
  (verify-at-outline)
- Verify-first clause: the consuming phase settles the HYPOTHESIS against the
  implementing source before scoping — refutation loops back to re-scope onto the
  correct owning surface.

## Expected Surface

- HYPOTHESIS: `marketplace/bundles/plan-marshall/skills/persona-plan-marshall-agent/` — foundational conduct rules (verify-at-outline)
- OBSERVED: `test/plan-marshall/persona-plan-marshall-agent/` — closure tests for the five conduct rules

## Dependencies and Sequencing

- Depends on: PLAN-04 (persona rules settled first — shipped, ordering only)
- Overlaps with: none in this epic (foundational persona surface touches no staged WS-01/02/03/05/06/07 surface)
- Adjacent to: PLAN-05/06 (dispatch-envelope contracts sit on the same persona base but touch execute-task/phase-6 dispatch files, not persona-plan-marshall-agent's own standard)

## Folded inbox material (same act)

- `lessons-handling-26-09-22-01-001.md` (candidate-lesson): persona-conduct cluster (5 lessons) — staged as this spec

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/process-compliance/plans/PLAN-14-persona-conduct-lessons.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
