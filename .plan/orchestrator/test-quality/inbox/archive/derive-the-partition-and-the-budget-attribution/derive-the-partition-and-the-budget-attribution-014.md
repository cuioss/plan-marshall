envelope_version=1
sender_type=plan
sender_id=derive-the-partition-and-the-budget-attribution
epic=test-quality
kind=candidate-lesson
created=2026-08-25T09:06:11Z

component=plan-marshall:automatic-review
category=bug
confidence=high
source_plan=derive-the-partition-and-the-budget-attribution

# review_completeness --measured-diff-size is the one flag the empty-is-safe guarantee does not cover

## Context

A `review_completeness check` call was rejected by argparse when
`--measured-diff-size` was interpolated with an empty value. The executor strips an
empty-string argument, so `--measured-diff-size ""` reaches the parser as a bare
`--measured-diff-size` with nothing after it, and a scalar option with no `nargs`
rejects that with "expected one argument".

The rejection is exit 2 — the script body never runs, so the whole completeness check is
lost rather than degraded.

## Root cause

Verified in source. `review_completeness.py` declares `--measured-diff-size` with
`default=''` and **no** `nargs='?'`. Every one of the eight LIST flags on the same
sub-parser (`--required-bots`, `--optional-bots`, `--participated-bots`,
`--in-progress-bots`, `--refused-bots`, `--stale-participation-bots`, `--declined-bots`,
`--unrecognised-refusal-bots`) does take an optional value, and the module docstring
states the guarantee explicitly:

> Every list flag above takes an OPTIONAL value: it may be supplied bare ... A caller that
> interpolates an empty variable into the command line therefore produces the empty-list
> reading rather than an argparse rejection.

The guarantee is scoped, accurately, to "every list flag". `--measured-diff-size` is a
scalar and sits outside it — and the flag's own help text says "Omit it (the default) when
unmeasured", which reads as an assurance that an unmeasured value is safe to pass through.
So the surface has one flag that behaves opposite to its eight neighbours, in a document
whose prose is about how safe an empty value is.

The relaxation was described at the time as "a parser-robustness change ONLY". It was
applied to the list flags because those were the ones observed failing; the scalar was
never in the population.

## Proposed action

Give `--measured-diff-size` `nargs='?'` with `const=''`, so a bare flag reads as the
documented unmeasured default. That makes the whole sub-parser uniformly
empty-interpolation-safe, and removes the one exception a caller has to remember.

Then state the guarantee over the flag set rather than over the list flags — "every
optional flag on this sub-parser may be supplied bare" is a claim a reader can rely on
without classifying each flag first.

## Evidence

- `review_completeness.py` — `--measured-diff-size`, `default=''`, no `nargs`
- same file, module docstring — the empty-is-safe guarantee, scoped to "every list flag"
- same file, flag help — "Omit it (the default) when unmeasured", which an empty
  interpolation cannot actually achieve
- observed: exit 2, argparse usage on stderr, the check never ran
