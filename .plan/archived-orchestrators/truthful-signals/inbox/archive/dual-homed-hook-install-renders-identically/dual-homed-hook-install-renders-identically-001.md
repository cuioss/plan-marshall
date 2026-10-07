envelope_version=1
sender_type=plan
sender_id=dual-homed-hook-install-renders-identically
epic=truthful-signals
kind=candidate-lesson
created=2026-09-03T09:46:54Z

component=plan-marshall:phase-6-finalize
category=improvement
confidence=high
source_plan=dual-homed-hook-install-renders-identically
source_aspects=plan_efficiency,llm_to_script_opportunities

# Scope a self-review fix to the finding class, not the instance it named

## Context

`pre-submission-self-review` fired 5 times over 10 rounds on PLAN-TRUTH-102 and found 13 defects, all genuine and all introduced by that diff. The cost split is the finding: rounds 1-5 cost 896,644 tokens; rounds 6-10 cost **953,588** — more, for fewer defects. Rounds 6-10 were largely residue of the previous round's own fixes, concentrated in two symmetric `marshall-steward` menu docs (`menu-enforcement-hook.md` and `menu-terminal-title.md`). Each round fixed the file the finding named; the next round found the sibling. Only at round 9 was a whole branch rewritten, and round 10 then showed the sibling file still carried the identical pair.

The step accounts for 1,850,232 tokens — **50.6%** of the plan's whole recorded dispatch spend — for defects that never reached the PR. The rounds-6-to-10 block alone is 26.1% of the plan.

## Root cause

A self-review finding names one file because that is where the surfacer matched. The fix is then scoped to the named file rather than to the class of documents that share the claim. Where the class is a known symmetric pair, this guarantees at least one further round per member, and the review loop pays a full round-trip to rediscover what the first round already implied.

`pm-plugin-development:ext-self-review-plan-marshall` already surfaces *near-identical-hunk touched claims* and *duplicate-claimable keys*, so the class is representable — it is the emission granularity that is per-instance.

## Proposed action

1. In `ext-self-review-plan-marshall`, emit a candidate that matches in N > 1 files **once**, as an N-member set carrying every member path, instead of N independent candidates.
2. In `phase-6-finalize/workflow/pre-submission-self-review.md`, state that a finding carrying more than one member path is fixed and re-checked across the whole member set in the same round; a fix that closes one member and leaves siblings open does not close the finding.

## Evidence

- aspect: plan_efficiency — `block_b_rounds_6_to_10_tokens: 953588` vs `block_a_rounds_1_to_5_tokens: 896644`; `self_review_cost.share_of_recorded_plan_total: 0.506`
- aspect: llm_to_script_opportunities — candidate "Re-reading two symmetric marshall-steward menu docs round after round to find the sibling of a fix", repetition_count 5
- `status.metadata.phase_steps["6-finalize"]["pre-submission-self-review"].display_detail`: "13 fixed over 10 rounds; final sibling deletion not re-reviewed"
- Estimate (uniform per-round cost, NOT a measurement): closing at round 7 instead of round 10 saves roughly 3 x 190,718 = 572,154 tokens, ~15.6% of the plan.
