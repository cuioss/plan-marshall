envelope_version=1
sender_type=plan
sender_id=post-merge-review-findings-untriaged-in-main
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T09:44:47Z

component=plan-marshall:workflow-integration-github
category=bug
created=2026-07-29
bundle=plan-marshall

# pr-agent never reviewed the merged SHA; the step was force-done anyway

pr-agent, the plan's only required bot, never reviewed the merged SHA despite two `/review` triggers
and roughly 23 minutes of awaiting. The `automatic-review` step was still marked done via the
force-done escape hatch, so the finalize pipeline proceeded as if the required review had happened.

## Solution

The force-done escape hatch is legitimate for advisory/optional bots but must not silently satisfy a
`required`-bot obligation. When a required bot never participates within the awaiting window,
force-done should still record the outstanding-required-bot fact in its `display_detail` (not just
"forced done") so downstream consumers (retrospective, epic landing) can see the gap instead of
reading a plain "done".

## Impact

Matches the epic's standing correction that "`ci pr comments` is necessary but NOT sufficient" and
that check states can lie in both directions — a review-bot that never ran can still leave the step
green. This plan's own run is a fresh, live instance of that exact failure mode, on the plan's only
required reviewer.
