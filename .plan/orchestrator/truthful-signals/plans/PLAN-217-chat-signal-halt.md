# PLAN-14: Chat-signal fidelity and halt reporting

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-07

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-14-chat-signal-halt.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.
>
> Reshaped 2026-09-19: the two test-infra lessons (TestFindSkillsRoot, shared
> script registration) transferred to test-quality PLAN-180 at operator
> direction — see lessons-disposition.md § Transfers out for their ids.
> Six deliverables remain.

## Objective

Keep the retrospective substrate faithful and halts explicit: chat-signal keeping
operator turns, transcript counts describing intact text, read-phase filters that do
not no-op, version stamps. G06 + 2 singletons (6 lessons).

## Deliverables

1. Operator-turn retention in extract-chat-signal (2026-09-04-14-002).
2. Wait-state narration on finalize gate halts (2026-09-03-11-006).
3. Continuation-announcement without progress treated as halt (2026-09-04-14-003).
4. Transcript counts describing intact text across TOON round-trip (2026-09-05-16-001).
5. read --phase covering decision and work logs correctly (2026-08-25-09-003).
6. Stamped skill version in sync-cache steps (2026-09-03-06-005).

## Claim Labels

- OBSERVED: extractor kept 1 of 13 operator turns, starving downstream aspects — read at `lessons-archive/2026-09-04-14-002.md` § Context.
- OBSERVED: reduced_transcript truncated/reordered while counts describe intact text — read at `lessons-archive/2026-09-05-16-001.md` (title triage; body verified at outline).
- HYPOTHESIS: turn-faithful extraction plus halt-vs-progress vocabulary restores the substrate — confirm/refute at `marketplace/bundles/plan-marshall/skills/plan-retrospective/scripts/` § extract-chat-signal (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-retrospective/` — chat-signal, transcript.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/manage-logging/` — read filters.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: none.
- Adjacent to: WS-01 retrospective aspects consume chat-signal without touching it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-217-chat-signal-halt.md"
```

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
