envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T22:04:39Z

component=plan-marshall:phase-6-finalize
category=bug
created=2026-07-29

# pre-submission-self-review is not in HEAD_DEPENDENT_STEPS, so it never re-fires over a loop-back diff

`pre-submission-self-review` is missing from the finalize dispatch loop's `HEAD_DEPENDENT_STEPS` set. When this plan looped back and the loop-back diff introduced the two real defects later captured as separate candidate lessons (the detector-scope regression and the fifth `detected`-mirror recurrence), the in-house structural self-review step did not re-fire over that new diff — it had already run once earlier in the plan and was not re-triggered by the HEAD-changing loop-back. Both defects were instead caught externally, by CodeRabbit and by the whole-tree test gate, not by the review step whose entire purpose is to catch exactly this class of defect before submission.

## Solution

Not fixed in this plan; filed as residue for the epic. A fix would add `pre-submission-self-review` to `HEAD_DEPENDENT_STEPS` in the phase-6-finalize dispatch loop so a loop-back diff re-triggers the in-house structural review.

## Impact

Any finalize step whose entire job is to inspect "the diff about to be submitted" must be a HEAD-dependent step — omitting it from that set silently downgrades it to "ran once, early," which is a coverage gap disguised as a clean signal. This is the same confident-signal-hides-a-caveat shape the truthful-signals epic tracks generally, now located at the dispatch-loop level rather than inside an individual detector.
