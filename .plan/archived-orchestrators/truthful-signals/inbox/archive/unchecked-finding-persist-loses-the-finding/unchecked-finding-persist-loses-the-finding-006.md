envelope_version=1
sender_type=plan
sender_id=unchecked-finding-persist-loses-the-finding
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T16:29:43Z

component=pm-plugin-development:ext-self-review-plan-marshall
category=improvement
created=2026-07-28

# Pre-submission self-review caught a defect the plan itself introduced

This plan's fix for unchecked finding-persist introduced a new call site in
`phase-4-plan` Step 8 that itself only parsed `total_failed`/`ambiguous` from its
result — a rejected persist would have been silently dropped at a call site the plan
introduced, one level up from the defect class it was fixing. Pre-submission
self-review caught this before merge, not a later audit.

## Solution

When a plan's fix touches a defect class (e.g., "unchecked persist"), explicitly sweep
the plan's OWN new call sites for the same defect shape as part of self-review — a fix
is a new producer/consumer pair and is exactly as liable to the defect as the sites it
corrects.

## Impact

Validates the value of running pre-submission self-review even on a plan whose whole
purpose is fixing this exact defect class — the fix itself is not exempt from
introducing a fresh instance.
