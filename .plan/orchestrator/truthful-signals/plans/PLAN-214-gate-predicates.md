# PLAN-11: Gate predicates and refine honesty

> ⛔⛔ **SUPERSEDED BY PM-MCP (2026-09-26, operator decision; row status `parked`).** `plan-marshall-mcp` replaces both the
> process prose and the Python scripts this plan edits, so implementing it here is legacy work. Its
> implementation-independent content (rules, invariants, classifications, data, fixtures) was extracted to
> `plan-marshall-mcp/doc/known-defects/truthful-signals-carry-over.md` as PM-MCP input.
> **Do NOT emit; un-park only by explicit operator decision.** The spec body below stays intact as the evidence chain.

epic: truthful-signals
workstream: WS-06

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-11-gate-predicates.md` and is queued in the epic `status.json`
> `plans[]` field. The orchestrator EMITS the command below; it never launches the
> plan inline. This spec is SELF-SUFFICIENT.

## Objective

Keep gate predicates honest: heuristics that cost nothing on clean
runs, exclusions at site granularity, handshake diagnostics, live-config bounds,
B7 carve-out for orchestrator handoffs, triage routes to rejected, STATUS barrier
hygiene. G20 + G25 + G07 + G11 + 1 singleton (8 lessons).

## Deliverables

1. Fixed-cost suspicion heuristics removed or made signal (2026-09-03-16-002).
2. Site-grained exclusions, no silent sibling exclusion (2026-09-03-16-003).
3. Orchestrator-tier-handoff carve-out in B7 no-progress (2026-08-25-09-005).
4. Triage route to rejected for in-triage refutation (2026-09-08-13-010).
5. Handshake verify diagnostics on empty-stderr failure (2026-09-03-19-006).
6. Handshake tolerance for legitimately decreased finding counts (2026-09-03-16-005).
7. Live-config bounds, never documented defaults (2026-09-07-13-001).
8. Bot STATUS bodies kept out of pending-findings barrier (2026-08-25-09-013).

(Retired 2026-09-19, all verified in-tree before retiring: transcript-less logged
decision — plan-marshall/workflow/execution.md logs the absent identity and
target before dispatching unenriched; session_id on transcript-less template —
SKILL/documented optional with gap-flag skip; commit-existence anchor validation
— _cmd_mark_step.py refuses non-resolving sha fail-closed with
unknown_head_at_completion, writing nothing.)

## Claim Labels

- OBSERVED: all-six-dimensions-100 suspicion fires as the normal outcome — read at `lessons-archive/2026-09-03-16-002.md` (title triage; body verified at outline).
- HYPOTHESIS: signal-graded heuristics plus site-grained exclusions retire the class — confirm/refute at `marketplace/bundles/plan-marshall/skills/phase-2-refine/` § suspicion heuristics (verify-at-outline).

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/phase-2-refine/` — suspicion heuristics, exclusions.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/plan-marshall/` — B7 predicate, handshake, triage.
- OBSERVED: `marketplace/bundles/plan-marshall/skills/workflow-integration-github/` — STATUS barrier.

## Dependencies and Sequencing

- Depends on: PLAN-10 (phase-5 primitives its gates read).
- Overlaps with: PLAN-10 — sequenced after it.
- Adjacent to: none.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/truthful-signals/plans/PLAN-214-gate-predicates.md"
```

## ⭐ FOLDED 2026-09-22 — D1 needs an orchestrated-spec-aware arm, with a cross-epic-owned derived population

Inbox lesson `2026-09-20-08-011` (relayed via `lessons-handling-26-09-22-01`, surfaced during
`orchestrator-refactor` PLAN-04 / PR #1543): orchestrator-authored staged specs systematically trip
phase-2-refine's suspicion heuristic. Six dimensions scoring 100 is EXPECTED for a spec an orchestrator
already pre-verified with OBSERVED/HYPOTHESIS claim labeling, not suspicious — the check needs an
orchestrated-spec-aware arm, the opposite prescription from D1's `2026-09-03-16-002` corpus lesson (which
that spec's own § FOLDED 2026-09-15 already records as accepted corpus learning, not open work). D1's
Expected Surface (`phase-2-refine/` — suspicion heuristics, exclusions) already covers the file; surface
unchanged. **Cross-reference, do not re-derive**: `orchestrator-refactor` independently tracks the derived
staged-spec 2-refine score population as its own Watch — read it before scoping the arm's threshold.

⚠ Header drift found and FIXED at the following `cleanup` pass (2026-09-22, A4 duplication cross-check):
this spec's front-matter read `epic: quality-aspect` and its Hand-Off Command pointed at
`.plan/orchestrator/quality-aspect/plans/PLAN-11-gate-predicates.md` — a path that no longer resolves at
all, since `quality-aspect` is archived (`archived-orchestrators/quality-aspect/`). The same drift was
found on all 15 migrated `PLAN-2xx` (ex `quality-aspect`) specs and corrected on all of them in the same
pass.

## Write-Boundary

The plan touches only its own repository source and tests. It creates and edits NO
file under `.plan/orchestrator/` other than its own `inbox/{sender}-{seq}`
message, and reports its outcome through its PR and its inbox message.
