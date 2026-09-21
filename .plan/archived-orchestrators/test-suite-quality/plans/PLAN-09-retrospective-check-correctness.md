# PLAN-09: plan-retrospective Check Correctness

epic: test-suite-quality
workstream: WS-03

> Staged plan spec — one shippable unit of work, ready for `/plan-marshall` hand-off.
> See `persona-marshall-orchestrator/standards/orchestration-model.md` for the hand-off contract.

## Objective

Repair the `plan-retrospective` checks that emit false verdicts — silent passes, dropped findings,
miswarnings, and gross overcounts. A retrospective that reports green when it measured nothing, or drops
the very findings it was meant to surface, is worse than no retrospective: it launders an unaudited plan
as audited. This is the consumer end of the same self-audit-chain failure PLAN-08 fixes at the producer
(finalize) end — kept separate because the surface (`plan-retrospective` scripts) is disjoint, enabling
parallel execution.

## Verified-open / to-verify inputs

| Lesson | Claim | Status |
|--------|-------|--------|
| `2026-07-22-22-001` | `check-artifact-consistency` affected-files regex cannot parse the canonical `` - `path` (intent) `` bullet → coverage reports `declared: 0`, then ∅-vs-∅ passes: **the declared-vs-achieved assertion never runs** | **verified open** — `_AFFECTED_FILE_BULLET_RE` at `check-artifact-consistency.py:65` anchors `` `?…`?\s*$ ``, so a trailing intent annotation fails to match |
| `2026-07-22-22-002` | `check-routing-decisions` attributes every absent prunable step to its prune predicate, misreporting posture-cutoff drops as `mis_prune` | verify at outline |
| `2026-06-20-17-003` | `chat-history-analysis` aspect is dead: a missing `SECTION_SPEC` row makes `collect-fragments` reject its key (findings keyed under it are dropped) | verify at outline |
| `2026-07-17-11-001` | `analyze-logs` `dispatch_clustering` overcounts re-entries (76 vs 7 actual) | verify at outline |
| `2026-07-22-12-002` | `extract-chat-signal` reduction keeps full skill bodies and empty user turns | verify at outline |

## Deliverables

1. **`check-artifact-consistency` — parse the canonical intent-annotated bullet.** Fix
   `_AFFECTED_FILE_BULLET_RE` (`check-artifact-consistency.py:65`) so `` - `path` (intent) `` is
   captured (path only, intent discarded), closing the double-false-green where `declared: 0` then
   ∅-vs-∅ passes. Add a regression test with the canonical bullet form so the coverage gate cannot
   silently void again.
2. **`check-routing-decisions` — distinguish a posture-cutoff drop from a mis-prune.** A step absent
   because the posture tier legitimately dropped it must not be reported as `mis_prune`. Infer the
   drop reason from the actual routing decision, not from mere absence.
3. **`chat-history-analysis` / `collect-fragments` — restore the dropped aspect.** Add the missing
   `SECTION_SPEC` row so `collect-fragments` accepts the key and the aspect's findings reach the
   report instead of being silently dropped.
4. **`analyze-logs` — fix the `dispatch_clustering` overcount.** Root-cause the 76-vs-7 re-entry
   overcount so the dispatch metric is trustworthy.
5. **`extract-chat-signal` — stop keeping full skill bodies and empty user turns** in the reduction,
   so the chat signal is the signal, not the transcript.

**Split-guard note:** five deliverables, at the ~6 presumption boundary but under it. They are a single
coherent surface (the `plan-retrospective` check/reduction scripts), each a small localized fix, and
they share regression-test scaffolding — kept as one plan per the operator's larger-plan preference.
If outline finds any single item balloons, split it out rather than dropping it.

## Lessons consumed — retire from the global store on landing

Retire each **only after confirming the plan resolves it**.

| Lesson | Resolved by |
|--------|-------------|
| `2026-07-22-22-001` | D1 |
| `2026-07-22-22-002` | D2 |
| `2026-06-20-17-003` | D3 |
| `2026-07-17-11-001` | D4 |
| `2026-07-22-12-002` | D5 |

## Expected Surface

- `plan-retrospective` scripts: `check-artifact-consistency.py`, the routing-decisions check,
  `collect-fragments` + its `SECTION_SPEC`/`retro_sections.py` registry, `analyze-logs`, and the
  `extract-chat-signal` reduction — confirm exact filenames at outline.
- Regression tests for each (these are checks that failed *open*; each needs a test that fails when the
  check is voided).
- **OFF-LIMITS**: the finalize dispatch machinery (PLAN-08's surface) and the audit-archived
  retrospective skill unless a shared helper genuinely spans both — flag if so rather than reaching in.

## Dependencies and Sequencing

- **Surface-disjoint from PLAN-07 and PLAN-08 → may run in PARALLEL with either.** This is the plan to
  emit first if parallel throughput is wanted.

## Hand-Off Command

```text
/plan-marshall Repair the plan-retrospective checks that emit false verdicts, verifying each lesson is still open before acting. A retrospective that reports green when it measured nothing, or drops the findings it was meant to surface, launders an unaudited plan as audited. Deliver: (1) fix check-artifact-consistency's affected-files regex (_AFFECTED_FILE_BULLET_RE at check-artifact-consistency.py:65) so it parses the canonical backtick-path-plus-intent bullet form ` - `path` (intent) ` (capture the path, discard the intent) — today it anchors to end-of-line right after the optional closing backtick, so a trailing intent annotation fails to match, coverage reports declared:0, and the strict peer then compares empty-vs-empty and passes, so the declared-vs-achieved assertion never actually runs (lesson 2026-07-22-22-001); add a regression test with the canonical bullet; (2) fix check-routing-decisions so a step absent because the posture tier legitimately dropped it is not reported as mis_prune — infer the drop reason from the actual routing decision, not from mere absence (lesson 2026-07-22-22-002); (3) restore the dead chat-history-analysis aspect by adding the missing SECTION_SPEC row so collect-fragments accepts its key instead of silently rejecting it and dropping its findings (lesson 2026-06-20-17-003); (4) fix the analyze-logs dispatch_clustering re-entry overcount (76 versus 7 actual) so the dispatch metric is trustworthy (lesson 2026-07-17-11-001); and (5) stop extract-chat-signal's reduction from keeping full skill bodies and empty user turns so the chat signal is signal not transcript (lesson 2026-07-22-12-002). Add a regression test for each — these checks failed OPEN, so each needs a test that fails when the check is voided. Confirm exact script filenames at outline. Do NOT reach into the finalize dispatch machinery or the audit-archived retrospective skill unless a shared helper genuinely spans both, in which case flag it. This plan RESOLVES lessons 2026-07-22-22-001, 2026-07-22-22-002, 2026-06-20-17-003, 2026-07-17-11-001 and 2026-07-22-12-002 — verify each is still open, then RETIRE the resolved ones from the lessons-learned store in finalize lessons-housekeeping since the fix consumes them; record (do not retire) any that outline finds already-fixed. Resolve all build commands through the architecture-resolved executor and read the TOON status and errors after each build call.
```

## Status Trail

- plan_marshall_plan_id: {set at launch}
- pr: {set when the PR opens}
- landing: {set when the landing analysis is recorded at landings/PLAN-09.md}
