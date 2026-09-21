# WS-02: Corpus-level auditing

epic: post-run-quality

> Charter document for one workstream. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

One plan's retrospective cannot see a trend; the archived-plan auditor is where cross-plan quality is
actually measured — 24 checks, era stamps, retire-on-quiet, and a suspect-zero census. This workstream
makes that instrument honest about itself, starting with the defect its own documentation names: the
census is excluded from its own population. It closes when every check's zero states which zero it is and
the auditor's self-exclusions are either removed or derived.

## Scope

- In scope: `.claude/skills/audit-archived-plan-retrospectives/**` (SKILL.md, `scripts/audit.py`, all 24
  `checks/*.md`), the era-stamp and retire-on-quiet meta-machinery, the suspect-zero census, the
  `input-integrity` no-false-healthy floor, and `.claude/skills/recipe-plan-review/**` as an unpersisted
  member of the same corpus-question population.
- Out of scope: the per-plan aspects that feed the corpus (WS-01); lesson quality (WS-03); the
  cloud-vs-local comparative reports under `doc/analyzis-cloud-plan/`, which are a completed experiment,
  not live machinery.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PRQ-03-the-census-does-not-census-itself-and-a-re-check-has-no-persisted-result | staged | The auditor's self-exclusion, plus the two corpus questions nothing can answer because their producer persists nothing |

## Sequencing and Surface Notes

- PLAN-PRQ-03's surface is **entirely project-local** (`.claude/skills/**`), which makes it disjoint from
  every other spec in this epic — the natural partner if `parallelization_scope` is ever raised above 1.
- ⚠ It shares `.claude/skills/audit-archived-plan-retrospectives/**` with `truthful-signals`
  PLAN-TRUTH-152's declared surface **only while that spec still exists**; the transfer retires it, so the
  overlap resolves on transfer rather than needing sequencing.
- Depends on nothing. Its D0 derives the check population from the checks directory, so it does not need
  WS-01 to land first.
