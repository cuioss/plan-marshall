envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T22:04:24Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=anti-pattern
created=2026-07-29

# Hand-maintained `detected` mirror recurred a fifth time, inside the fix meant to eliminate it

The truthful-signals epic has now seen four prior instances of a hand-maintained mirror of a computed `detected`/status value drifting from its source of truth. TASK-008's registry fix in this plan (targeting a related signal-accuracy defect) introduced a fifth such mirror in its own diff. It was caught only because the dispatch prompt explicitly demanded an adversarial re-read of the fix's own diff for the same defect class — no automated check or the in-house self-review flagged it on its own.

## Solution

Caught and corrected in-run via the demanded adversarial re-read before submission.

## Impact

A fix targeting any "signal accuracy" or "mirror drift" defect class must itself be diffed for the same defect class before submission — a hand-maintained mirror of a computed value inside the corrective diff is presumptively suspect, not presumptively safe just because it's part of the fix. Consider whether this check belongs as a standing structural self-review candidate (a "does this fix introduce another instance of what it fixes" check) rather than relying on the dispatch prompt to demand it ad hoc.
