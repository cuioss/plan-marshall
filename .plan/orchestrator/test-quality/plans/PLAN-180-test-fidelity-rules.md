# PLAN-180: Test-fidelity rules the suite can mean

epic: test-quality
workstream: WS-01

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> Lives at `plans/PLAN-180-test-fidelity-rules.md` and is queued in the epic
> `status.json` `plans[]` field. The orchestrator EMITS the command below; it never
> launches the plan inline.
> This spec is SELF-SUFFICIENT: the emitted command is a one-line pointer and carries no
> brief, so every per-plan carry is authored here and nowhere else.
>
> Provenance: transferred from `quality-aspect` (2026-09-19 full-corpus ingestion) at
> operator direction — test-fidelity material belongs to this epic. Lesson evidence
> lives at `.plan/orchestrator/quality-aspect/lessons-archive/{id}.md`.

## Execution Contract

The executing plan complies strictly with the plan-marshall process and rules: it
runs the phased lifecycle through its managing skills, treats this spec as the binding
brief, verifies every HYPOTHESIS and verify-first clause against the implementing
source before scoping on it, honors the Write-Boundary below, and reports back through
its PR and its inbox message. Standing operator instruction for this epic (opencode): process compliance is mandatory, not advisory.

## Objective

Make the green suite mean it: argv constants the CLI actually accepts, temp-root
pruning that cannot eat the session, mirrors pinned to published seams, splits
carved by behavior cluster, and test-infra registration done once. Done when every
new fidelity rule carries a negative control and the suite reports no new skips.

## Deliverables

1. Hoisted base argv restricted to CLI-accepted forms (lesson 2026-09-03-07-007).
2. Temp-root pruning scoped off the session's own tmp_path (lesson 2026-09-03-22-001).
3. Project-wide tool-default changes invalidating every stating document (lesson 2026-09-14-05-006).
4. Test-side mirrors pinned to published seams, not hoisted into source (lesson 2026-09-13-12-010).
5. Fixture docstrings saying yield only when the fixture yields (lesson 2026-09-13-12-011).
6. Oversized mechanical splits carved by behaviour cluster into independently-mergeable PRs (lesson 2026-09-18-11-001).
7. TestFindSkillsRoot reading the live module object (lesson 2026-09-03-17-001).
8. Single registration when splitting a test module over a shared script module (lesson 2026-09-17-15-001).
9. pytest basetemp relocated out of agent scratch (lesson 2026-09-03-02-005).

## Claim Labels

- OBSERVED: hoisted base argv carried mutually exclusive flags, fidelity claim false — read at `.plan/orchestrator/quality-aspect/lessons-archive/2026-09-03-07-007.md` § Context.
- OBSERVED: a test driving pruning production code deleted the session's own tmp_path — read at `.plan/orchestrator/quality-aspect/lessons-archive/2026-09-03-22-001.md` (title triage; body verified at outline).
- HYPOTHESIS: CLI-validated argv constants plus scoped pruning plus seam-pinned mirrors hold the suite honest — confirm/refute at `marketplace/bundles/plan-marshall/skills/persona-module-tester/` § fidelity rules (verify-at-outline).
  - verdict: corroborated | checked_at: 1e2aa916a474bedeff2118b19dffd329227308b8 | by: test-quality/analyze | rescoped: n/a | evidence: ada9d8d6 lands all 8 remaining deliverables with guards plus matched negative controls, no new skips; D5 already landed as cd6436a4a

## Expected Surface

- OBSERVED: `marketplace/bundles/plan-marshall/skills/persona-module-tester/` — fidelity rules.
- OBSERVED: `marketplace/bundles/pm-dev-python/skills/pytest-testing/` — mirrors, splits, basetemp.

## Dependencies and Sequencing

- Depends on: none.
- Overlaps with: PLAN-177 (plugin-doctor/test surfaces are adjacent, non-identical) — sequence after PLAN-177 lands.
- Adjacent to: WS-05 suite-integrity without touching it.

## Hand-Off Command

```text
/plan-marshall task="implement .plan/orchestrator/test-quality/plans/PLAN-180-test-fidelity-rules.md"
```

## Write-Boundary

The plan implementing this spec touches only its own repository source and tests. It creates
and edits NO file under `.plan/orchestrator/` other than its own
`inbox/{sender}-{seq}` message — the orchestrator owns every other ledger write — and reports
its outcome through its PR and its inbox message.
