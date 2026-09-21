envelope_version=1
sender_type=plan
sender_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-13T12:34:04Z

# Candidate lesson: resolve base refs to exactly one commit object

## Context

Both footprint-base resolvers ran bare `git rev-parse <ref>`, whose
output can be multi-line (revision ranges) or a non-commit object
(annotated tags). Hardened in 6af1753 to
`rev-parse --verify --end-of-options <ref>` with single-SHA validation,
then in bae76c059 with a `^{commit}` suffix, with regression tests for
option-like and range refs.

## Observation

A reported SHA field needs all three guards — option termination,
single-revision verification, and commit-object peeling — because each
closes a different non-SHA output shape.
