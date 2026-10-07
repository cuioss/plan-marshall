envelope_version=1
sender_type=plan
sender_id=prompt-standard-and-doctor-rule
epic=operator-ux
kind=candidate-lesson
created=2026-09-02T13:41:08Z

component=plan-marshall:phase-6-finalize
category=anti-pattern
confidence=high
source_plan=prompt-standard-and-doctor-rule
recurrence_of=none

# Apply the convergent resolution a self-review finding states, not a narrowing reword

## Context

`pre-submission-self-review` fired five times on this plan (`firing_count: 5`, four prior `failed`) and filed eleven findings, every one `defect_class contract_drift`, every one resolved by deletion in the end. The eleven were not evenly distributed across independent defects: rounds 3 and 4 filed seven of them, and at least three name an earlier round's own fix as their source.

- `45f9f0` and `977805` (round 3) both open with the literal words *"SELF-SEEDED by round 2"*.
- `276d72` (round 4) reads: *"Round 1 adopted this sentence as the 'true, narrower fact'; it is narrower but still false."*
- `ebbf9b` (round 4) reads: *"This is the round-1 clause with 'verdict' replaced by 'finding'; it was never swept out of the script."*

Round 1's own finding text (`7d498d`) had already stated the answer: *"Convergent fix is DELETION of the over-claiming clause; the analyzer docstring already states the true, narrower thing."* The fix narrowed the clause instead of deleting it, and round 4 filed the narrowed form as still false.

## Root cause

The round-loop termination rule in `phase-6-finalize/workflow/pre-submission-self-review.md` names self-seeding as the failure mode and prescribes deletion as the convergent resolution. The rule governs how a finding is *classified and reported*; nothing governs the *fix* applied between rounds. When a finding says "this prose claims more than the code delivers", a reword that claims slightly less is locally plausible and passes the author's own reading — and re-enters the next round's candidate set. Deletion is the only edit that cannot seed.

The finding text itself carried the correct instruction on the very first round. It was read and not followed, twice.

## Proposed action

Make the convergent-resolution instruction binding on the fix, not just on the report:

1. When a self-review finding's own `rationale` names DELETION as the convergent resolution, the loop-back fix MUST delete. A narrowing reword of the same clause is not an admissible fix for that finding and should re-open it.
2. Have the next round's candidate surfacer flag any candidate whose text was authored by a prior round of the same step (the `head_at_completion` anchors already scope each round's delta, so the provenance is recoverable) and report it as self-seeded *before* the round spends tokens re-deriving that classification by hand.

## Evidence

- aspect: chat_history_analysis — all four loop-backs are the self-review loop re-entering itself inside `6-finalize`
- qgate findings `7d498d` (round 1, prescribes deletion), `45f9f0` / `977805` (round 3, labelled SELF-SEEDED by round 2), `276d72` / `ebbf9b` (round 4, name round 1's fix as their source)
- aspect: plan_efficiency — rounds 3 and 4 account for 7 of 11 findings; `self_review_recorded_tokens=677934` across four of five firings, a floor
- Existing active lesson `2026-08-25-09-007` already proposes a generic self-seeding *guard*; this is the sharper, cheaper precondition — follow the resolution the finding already states
