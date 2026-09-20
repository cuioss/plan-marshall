envelope_version=1
sender_type=plan
sender_id=architecture-store-query-truthfulness
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-09-15T07:56:26Z

component=plan-marshall:manage-tasks
category=bug

# `int(1.5)` silently gave a fractional record deliverable 1's identity

Source: PR #1489 CodeRabbit inline finding 88d743 (resolution=fixed, TASK-039).

`_as_int(1.5)` returns `int(1.5) == 1`, so a fractional deliverable number silently takes
deliverable 1's identity inside index_unique_by_number, and the gap and completeness
results are computed over a corrupted key set.

The asymmetry is what makes it invisible: `_as_int('1.5')` already returns None via
ValueError, so the STRING path rejects the value and the FLOAT path silently truncates
it. A coercion helper that is strict on one input type and lossy on another reads as
validated.

## Solution

Accept integers and integer-valued strings only; reject booleans and non-integral
numerics.

## Impact

Changes record IDENTITY, which corrupts every downstream set operation rather than
producing a visible error.
