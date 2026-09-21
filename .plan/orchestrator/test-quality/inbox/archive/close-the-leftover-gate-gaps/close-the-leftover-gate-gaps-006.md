envelope_version=1
sender_type=plan
sender_id=close-the-leftover-gate-gaps
epic=test-quality
kind=candidate-lesson
created=2026-09-19T09:20:03Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
source_finding=e7f6aa
source_phase=6-finalize
source_type=qgate
signal=signal_qgate_pending_count

# Bounded verdict with structural limit still owes a round: behavior unchecked

Verified 38 candidates over full 6 files; verdict bounded so accepted, but third close condition failed because a structural limit left behavior unchecked.

## Observation

Q-Gate finding `e7f6aa` (further_round_owed, 6-finalize) recorded the owed round. Superseded in-run when the re-examination round ran and converged to done at HEAD b8cce0470.

## Candidate lesson direction (for orchestrator classification)

Name the structural limit explicitly in the verdict so the owed round has a bounded scope; close only on a clean re-examination pass at the same HEAD.

## Source

Plan close-the-leftover-gate-gaps, 6-finalize pre-submission-self-review, resolution superseded 2026-09-18.
