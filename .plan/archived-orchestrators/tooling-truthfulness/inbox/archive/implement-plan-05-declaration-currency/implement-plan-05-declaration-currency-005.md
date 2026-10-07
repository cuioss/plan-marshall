envelope_version=1
sender_type=plan
sender_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-13T12:34:17Z

# Candidate lesson: preserve the actual unevaluated derivation state

## Context

Declaration-currency reported every unevaluated spec row as
`unreadable`, collapsing the `absent` (declared no surface) versus
`unreadable` (could not read) distinction that `_surface_state`
returns. Fixed in 6af1753 by reporting the returned state verbatim,
with a regression test.

## Observation

A row-builder default that overwrites a classified state destroys the
classifier's vocabulary downstream; report the classified state and let
consumers decide.
