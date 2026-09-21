envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:58:49Z

# Key finalize step re-fire on a content digest, not on head_at_completion

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source=plan-retrospective
source_plan=build-gates-test-suite-confidence-ci-workflow-lint

## Context

Every finalize step record stamps `head_at_completion` — a COMMIT sha. Any HEAD advance therefore invalidates every step record, including an advance that cannot possibly change a given step's verdict.

This run paid for that repeatedly. Mid-finalize the branch was found CONFLICTING with main and was rebased across 24 commits; the rebase re-staled the whole settle band and forced a full re-fire. Two whole-suite verify runs were spent re-certifying a tree whose content had not changed. The resulting firing counts:

- `pre-submission-self-review` — 14
- `pre-push-quality-gate` — 12
- `project:finalize-step-lessons-housekeeping` — 11, returning the identical verdict (`0 rm, 0 promo, 0 adapt, 66 keep`) every time
- `project:finalize-step-plugin-doctor` — 11
- `automatic-review` — 10, `ci-verify` — 7

6-finalize consumed 5,349,287 tokens, 74% of the plan's total and 15.3x what 5-execute spent. 1,012,148 of those went to 6 dispatches that terminated `error` with `retryable_total_tokens: 0` — spend that bought no step completion at all.

## Root cause

A commit sha is a poor proxy for "did anything this step reads change". It moves on rebase, on an unrelated sibling's landing, and on any commit touching any path. The verdict a step computed is a function of CONTENT, so the invalidation key should be content too.

## Proposed action

Stamp a `verdict_inputs_digest` alongside `head_at_completion`:

- when the step declares `verdict_inputs`, digest that glob set (`git hash-object` over the resolved paths);
- when it does not, fall back to `HEAD^{tree}`.

Skip the re-fire when the digest matches, regardless of whether the sha moved.

**Honest limit.** This particular rebase hand-resolved conflicts in 3 of 24 commits over 7 files, so a whole-tree digest would NOT have matched and the undeclared-surface steps would still have re-fired. The saving comes from (a) the path-scoped comparison for steps whose inputs miss those 7 files, and (b) the ordinary conflict-free rebase, where the tree is byte-identical and today's key still invalidates everything.

**Sibling, not duplicate.** Carried finding `dbce22` asks `lessons-housekeeping` to DECLARE a `verdict_inputs` surface it currently omits. This proposal is the complementary half: the COMPARISON BASIS is wrong even once a surface is declared. Both are needed; neither subsumes the other.

## Evidence

- aspect: plan_efficiency — `[BUDGET]` error, 7.18M tokens against a 2.0M `multi_module+bug_fix` error anchor (3.6x), dominant phase `6-finalize=5349287`
- aspect: logging_gap_analysis — 6/36 finalize dispatches `error`, 1,012,148 tokens, `retryable_total_tokens: 0`
- aspect: llm_to_script_opportunities — candidate 3, complexity `medium`, repetition_count 14
- `status.metadata.phase_steps` firing counts and `head_at_completion` values above
