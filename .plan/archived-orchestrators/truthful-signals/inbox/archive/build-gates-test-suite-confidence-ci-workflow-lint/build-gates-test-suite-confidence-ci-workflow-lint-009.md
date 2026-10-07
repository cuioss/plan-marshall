envelope_version=1
sender_type=plan
sender_id=build-gates-test-suite-confidence-ci-workflow-lint
epic=truthful-signals
kind=candidate-lesson
created=2026-08-25T14:58:38Z

# Terminate the self-review loop on self-seeding, not on an empty round

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
confidence=high
source=plan-retrospective
source_plan=build-gates-test-suite-confidence-ci-workflow-lint

## Context

The pre-submission-self-review settle band on this plan ran 3 rounds producing 4, 4 and 2 findings. Six of those ten findings were authored by the previous round's own fix:

- Round 2's findings `383a70`, `a61ed7` and `31de1f` each name round 1's fix commit `618f3af96` as the introducing change.
- Both round-3 findings (`c33703`, `57f8a4`) state that round 2's deletion caused them.

The step fired 14 times in total across the run and 8 of its 13 prior firings recorded `outcome: failed`. The loop was ultimately stopped by a human reading of the pattern, not by its own predicate — and only after the loop-back ceiling had been raised from 3 to 8.

## Root cause

The loop's termination predicate is "this round found nothing new". That predicate cannot distinguish convergence from oscillation, because an oscillating loop never produces an empty round — every round's fix authors the next round's finding, so the predicate can only ever terminate it by exhausting the iteration ceiling. The signal that separates the two states is not the finding COUNT but the finding PROVENANCE, and provenance is never consulted.

## Proposed action

Add a deterministic self-seeding classifier to the round loop. It needs no judgement and no new data:

1. Record each round's fix commit sha (already available — the evidenced-resolution path stamps it).
2. At round N+1, compute `git diff --name-only {round N fix sha}..HEAD`.
3. Intersect that set with the `file_path` of every finding round N+1 filed.
4. When the intersection is TOTAL — every new finding cites a file the previous round's own fix touched — stamp the round `self_seeded: true` and terminate the loop instead of iterating.

The LLM keeps the judgement it is good at (is this finding real?). Only the termination CLASSIFICATION becomes deterministic. Roughly 15 lines of set arithmetic over data the loop already holds.

Note the classifier would have fired on this run at round 2 and again at round 3, i.e. it would have saved two of the three rounds.

## Evidence

- aspect: logging_gap_analysis — 6 of 36 finalize dispatches terminated `error`, consuming 1,012,148 tokens with `retryable_total_tokens: 0`
- aspect: plan_efficiency — pre-submission-self-review fired 14 times; 8 of 13 prior firings recorded `failed`; 6-finalize consumed 74% of plan tokens
- aspect: llm_to_script_opportunities — candidate 5, complexity `low`, repetition_count 3
- qgate findings `383a70` / `a61ed7` / `31de1f` (round 2, naming commit `618f3af96`) and `c33703` / `57f8a4` (round 3, naming round 2's deletion)
