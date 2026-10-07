# WS-03: The learning loop

epic: post-run-quality

> Charter document for one workstream. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

A post-run analysis that changes nothing is a cost with no yield. This workstream owns the half of the
machinery that is supposed to close the loop — finding → lesson → governing contract — and the corpus
that accumulates in between: 194 lessons today, with provenance, dedup, retirement and a three-gate
creation policy. It closes when the loop is MEASURED rather than assumed: the share of lessons that reach
a contract is derivable, and a lesson's provenance survives the plan that filed it.

## Scope

- In scope: `manage-lessons/**` (creation policy, dedup analysis, aggregate, retire-quiet,
  cleanup-superseded, list-stalled, restore-from-plan), the lesson corpus's provenance and quality fields,
  `.claude/skills/finalize-step-lessons-housekeeping/**`, and the measurement of whether a filed lesson
  ever reaches the skill or standard it governs.
- Out of scope: the retrospective aspect that PROPOSES lessons (WS-01 owns the producer); where a finding
  should be ROUTED across repositories, which is `lessons-routing`'s subject by the standing
  destination-not-subject test.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PRQ-05-lessons-corpus-provenance-and-quality | staged | Transferred from `next-level` PLAN-09 — the corpus nobody has evaluated, now with the 1-in-5 contract-reach ratio as its outcome metric |

## Sequencing and Surface Notes

- ⚠ **Boundary with `lessons-routing`, restated because it is the one people get wrong**: a defect IN
  `manage-lessons`' behaviour is ours; a question about WHO should receive a finding and whether it
  reaches them is theirs. PLAN-PRQ-05 is the first kind.
- PLAN-PRQ-05 declares `manage-lessons/**`, which `truthful-signals` PLAN-TRUTH-144 also declares. ⛔ Those
  two must not run concurrently — and they sit in different epics, so **no gate can see the collision**.
  The constraint is recorded here and in PRQ-05's own Dependencies section, because a ledger cannot see a
  duplicate in another ledger.
- The outcome metric (`1 of 5 process lessons reached the governing contract`) is a corpus measurement:
  re-deriving it is WS-02's instrument, so PRQ-05 consumes PRQ-03's population work if that lands first,
  and derives it itself otherwise.
