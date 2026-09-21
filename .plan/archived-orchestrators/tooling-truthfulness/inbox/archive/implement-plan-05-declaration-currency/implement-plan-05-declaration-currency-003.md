envelope_version=1
sender_type=plan
sender_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-13T12:33:52Z

# Candidate lesson: apply declaration containment in the landing delta

## Context

`compute_surface_delta` used exact set subtraction, so a realized file
beneath a declared `test/` or `test/**` entry reported a false landing
expansion. Fixed in 6af1753 with a `_delta_covers` containment helper
mirroring the D1 rule, plus focused tests.

## Observation

Two comparisons over the same declaration vocabulary must share one
containment rule; an exact-subtraction twin of a containment-aware
comparison false-positives on every directory claim.
