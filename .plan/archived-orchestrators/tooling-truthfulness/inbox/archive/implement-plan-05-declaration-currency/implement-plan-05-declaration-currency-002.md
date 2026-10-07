envelope_version=1
sender_type=plan
sender_id=implement-plan-05-declaration-currency
epic=tooling-truthfulness
kind=candidate-lesson
created=2026-09-13T12:33:39Z

# Candidate lesson: count exclusions actually taken, not flags set

## Context

`corpus declaration-currency` reported `specs_excluded: 1` whenever
`--exclude-spec` was passed, even when the name matched no spec, breaking
`specs_scanned + specs_excluded == specs_total`. Fixed in f86e53e by
counting actual exclusions during iteration, with a regression test for
the non-matching case.

## Observation

Count fields derived from a flag's presence rather than from the loop
that acts on it misreport whenever the flag names nothing. Prefer
counting the action taken.
