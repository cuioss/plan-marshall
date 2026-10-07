envelope_version=1
sender_type=plan
sender_id=crashed-participation-gate-records-a-pass
epic=review-apparatus
kind=candidate-lesson
created=2026-08-01T19:05:51Z

component=plan-marshall:workflow-integration-github
category=bug
bundle=plan-marshall

# A bot comment carrying the documented ignore-pattern marker still survived the noise pre-filter into the findings ledger

On PR #1070, CodeRabbit's **auto-generated acknowledgement** carried the documented ignore-pattern marker — the exact marker the noise pre-filter exists to match — and was nevertheless filed as a finding in the ledger.

The pre-filter is therefore vacuous for at least this input: the marker is present, the filter is configured to drop it, and the comment lands anyway. A guard that does not fire on the one input it was written for is not a guard.

## Solution

1. Establish why the match failed before changing the pattern — normalization (whitespace, HTML comment wrapping, collapsed markup in the API body vs the rendered body) is the likely divergence, and a widened pattern that papers over a normalization bug will drift again.
2. Add a fixture built from the **actual** API-returned comment body for this ACK, not a hand-retyped approximation. The retyped version is what makes this class of test pass while the real input keeps failing.
3. Add a vacuity guard: assert the fixture population is non-empty and that at least one fixture is dropped by the filter, so an inert filter cannot report success on an empty match set.

## Impact

Noise that reaches the findings ledger costs triage time and, more importantly, inflates the actionable-comment count that downstream gates and the review-retrospective read. A bot's own refusal ACK counted as a finding is a signal that reports work where there is none — the same false-signal family as counting a check conclusion as participation evidence.
