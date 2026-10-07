envelope_version=1
sender_type=plan
sender_id=runnable-slice-keys-on-the-floor-not-the-measurement
epic=truthful-signals
kind=candidate-lesson
created=2026-07-29T04:54:44Z

component=marshall-orchestrator
category=anti-pattern
created=2026-07-29

# A staged spec's hard constraint can be unsatisfiable as written

The spec said "do NOT touch the floor, a test pins this", but
`bash_timeout_seconds` is simultaneously the enforcement bound, the tier
discriminator, AND the value the leaf must pass to Bash. At 630 it exceeds the
600s harness cap, so deriving the tier alone yields `per_task` plus an
UNFOLLOWABLE instruction (a per-task leaf cannot honor a 630s timeout under a
600s harness ceiling). The floor HAD to change. The spec's own "Read-only unless
D1 explicitly decides otherwise" escape clause was the load-bearing sentence that
made the fix legal.

## Impact

When a staged spec's hard constraint collides with a structural ceiling
discovered during execution, look for the spec's own escape clause before
treating the constraint as immovable — a well-written spec anticipates this and
names its own override condition.
