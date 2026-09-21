envelope_version=1
sender_type=plan
sender_id=generic-charter-language-specific-defect
epic=review-apparatus
kind=candidate-lesson
created=2026-08-09T16:49:07Z

# plan-retrospective's finalize position denies it both the footprint and the token total it measures

component: plan-marshall:plan-retrospective
category: bug
confidence: high
source_aspects: artifact_consistency, plan_efficiency

## Context

`plan-marshall:plan-retrospective` sits at position 17 of 22 in the finalize manifest — after `branch-cleanup` (13) and before `record-metrics` (20). Both neighbours starve it, in the same run, of the two inputs its two quantitative aspects exist to consume:

**Footprint.** `branch-cleanup` removes the worktree. `check-artifact-consistency` then derives the plan footprint from "the live worktree diff, falling back to `references.modified_files` for archived plans" — neither exists — and returned `inconclusive` for both `affected_files_recall` and `affected_files_exact_match`, over 31 declared files. The declared-vs-achieved coverage comparison, which is the deterministic item-coverage half of the thoroughness dial, produced no verdict at all. Reconstructing it by hand from the landed squash commit `f5493b437` took one `git show --name-only` and yielded a clean answer: 23 of 23 declared host-repo paths landed, 100 percent recall, plus 5 undeclared files. That answer was available the whole time; the aspect simply had no way to reach it.

**Tokens.** `record-metrics` has not yet run, so `metrics.md` carries `> Partial: unrecorded phases — 6-finalize` and a Total of `2,997,744 (n=4/6)`. Every `plan-efficiency` anchor and all four mandated ratios were therefore scored against a number that omits the entire finalize phase — whose own dispatch-boundary rows sum to **1,122,510 tokens**, roughly 37 percent more than the figure scored. `total_tokens_per_deliverable` computes to 374,718 and reads as under the 500,000 fallback threshold; on the completed total it is 515,032 and **crosses**. The threshold verdict is inverted by the ordering alone.

## Root cause

The retrospective is scheduled among the steps whose output it audits rather than after them. It is not a measurement problem — both inputs exist and are cheaply derivable — it is purely a position problem, and it reproduces identically on every plan that runs the standard finalize manifest.

## Proposed action

1. Teach `check-artifact-consistency` a post-cleanup fallback: when no worktree is on disk and `references.modified_files` is absent, resolve the plan's landed commit (`branch-cleanup`'s `head_at_completion` and the recorded PR number are both already in `status.metadata`) and derive the footprint with `git show --name-only --format=`. Today the aspect returns `inconclusive` for every plan finalizing under the current manifest order, so its non-inconclusive path is effectively dead.
2. Either move `record-metrics` ahead of `plan-retrospective` in the default finalize order, or have `plan-efficiency` fold the phase's own `work/metrics-dispatch-boundaries-6-finalize.toon` rows into its total. If neither is done, the aspect MUST stop scoring anchors silently against a partial and instead label every ratio a floor.
3. This corroborates retained lesson `2026-08-08-20-004` (record-metrics still ordered after plan-retrospective) from a second, independent direction, and shows the ordering defect has a second victim (`branch-cleanup` → footprint) that the existing lesson does not name.

## Evidence

- aspect: artifact_consistency — `affected_files_recall: inconclusive`, `footprint_resolved: false`, `declared: 31`
- aspect: plan_efficiency — `totals.tokens: 2997744` marked `PARTIAL (n=4/6)`; `unrecorded_phase_token_estimate.estimated_tokens: 1122510`
- metrics.md — `> Partial: unrecorded phases — 6-finalize`; Total row `2,997,744 (n=4/6)`
- execution.toon `phase_6.steps` — `branch-cleanup` at 13, `plan-marshall:plan-retrospective` at 17, `record-metrics` at 20
- retained lesson `2026-08-08-20-004` — the same ordering defect, seen from the metrics side only
