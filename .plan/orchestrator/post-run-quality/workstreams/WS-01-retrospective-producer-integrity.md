# WS-01: Retrospective producer integrity

epic: post-run-quality

> Charter document for one workstream. See
> `persona-plan-orchestrator/standards/orchestration-model.md` for the tier contract.

## Charter

The 16 aspects of `plan-retrospective` are the project's primary post-run judgement, and several of them
publish a confident figure over a population they never read. This workstream makes every aspect state
what it examined, so a reader can tell *checked and clean* from *never looked* — and makes the quality
chain that consumes those aspects produce a score with a stated basis rather than an unweighted verdict.
It closes when every registered aspect publishes its population and no aspect's clean reading is silence.

## Scope

- In scope: `plan-retrospective/**` (SKILL.md, standards, references, all aspect scripts), the
  `ext-point-retrospective` contract and its one implementor, the assessment-grading path shared with
  `manage-findings`, and the quality-chain scoring consumer.
- Out of scope: the corpus-level auditor over archived plans (WS-02); the lessons corpus and the
  finding→lesson→contract loop (WS-03); obligations that outlive a plan (WS-04); reviewer-quality
  measurement, which belongs to `review-apparatus`.

## Plans

| Plan | Status | Notes |
|------|--------|-------|
| PLAN-PRQ-01-retrospective-quality-chain-and-assessments-graded-at-report-time | staged | Transferred from `truthful-signals` PLAN-TRUTH-152: the quality chain has no score, a disabled gate reads like a clean one, and an assessment is graded at report time against a tree that moved |
| PLAN-PRQ-02-retrospective-aspects-publish-a-verdict-over-a-population-they-never-read | staged | Three measured producers plus the dispatch audit's caller-blindness — each states its population or degrades to a named could-not-look |

## Sequencing and Surface Notes

- ⛔ **PLAN-PRQ-01 and PLAN-PRQ-02 both declare `plan-retrospective/scripts/`** — never pair them, and at
  `parallelization_scope: 1` that is automatic. PRQ-02 is the narrower of the two and is the better first
  launch: its fixes are per-producer and land independently, while PRQ-01's D0 re-grounds 11 carried
  deliverables.
- PLAN-PRQ-01 carries `manage-findings/**` and `phase-3-outline/**` from its source spec; PLAN-PRQ-05
  (WS-03) also touches `manage-lessons/**` but not those — no overlap.
- The `check-manifest-consistency` fix in PRQ-02 interacts with the finalize step ORDER (retrospective is
  step 17, `branch-cleanup` is 13): the remedy must not assume the diff is available, because by
  construction it is not.
