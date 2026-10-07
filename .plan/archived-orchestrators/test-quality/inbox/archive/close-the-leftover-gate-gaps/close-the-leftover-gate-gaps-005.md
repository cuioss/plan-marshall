envelope_version=1
sender_type=plan
sender_id=close-the-leftover-gate-gaps
epic=test-quality
kind=candidate-lesson
created=2026-09-19T09:19:59Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
source_finding=b2a91d
source_phase=6-finalize
source_type=qgate
signal=signal_qgate_pending_count

# Re-examination round owed before close: verdict accepted but close condition failed

Pre-submission self-review verdict matched delta scope and coverage so accepted, but 1 finding failed the no-finding close condition, owing a further round.

## Observation

Q-Gate finding `b2a91d` (further_round_owed, 6-finalize) recorded the owed round. Superseded in-run when the re-examination round ran and converged to done at HEAD b8cce0470.

## Candidate lesson direction (for orchestrator classification)

Treat an accepted-but-not-closed verdict as an owed re-examination round rather than a close; converge via a second consecutive clean pass.

## Source

Plan close-the-leftover-gate-gaps, 6-finalize pre-submission-self-review, resolution superseded 2026-09-18.
