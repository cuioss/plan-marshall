envelope_version=1
sender_type=plan
sender_id=self-review-cannot-see-an-unreachable-guard
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T22:04:18Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=bug
created=2026-07-29

# New self-review detector reproduced its own target archetype

This plan built `ext-self-review-plan-marshall` to catch defects where a detector's implementation contradicts its own documented invariant. Its own new detector then committed exactly that defect: `_key_consumed_as_identity` was documented as diff-only in scope, but its implementation scanned the full post-image instead. The plan's in-house pre-submission self-review reported clean; CodeRabbit caught the mismatch in PR review, not the tool built for this purpose.

## Solution

Fixed in-run once CodeRabbit surfaced it; the diff-only scope was restored to match the documented invariant.

## Impact

Whenever a plan authors or extends a self-review detector, the detector's own implementation must be adversarially re-read against its own documented invariant before submission — "the detector exists" is not evidence the detector honors its own stated scope. Treat this the same as any other self-review candidate: a detector-authoring plan owes the detector's own diff a self-review pass, not just its target files.
