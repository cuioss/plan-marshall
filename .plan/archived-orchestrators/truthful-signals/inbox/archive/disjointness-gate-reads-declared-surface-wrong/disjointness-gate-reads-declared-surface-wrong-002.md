envelope_version=1
sender_type=plan
sender_id=disjointness-gate-reads-declared-surface-wrong
epic=truthful-signals
kind=candidate-lesson
created=2026-08-30T10:34:25Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
source_plan=disjointness-gate-reads-declared-surface-wrong
source_pr=1366

# A cardinality check cannot discharge a membership requirement

## What happened

PLAN-TRUTH-113 exists because the disjointness gate compared the wrong surface. Its
round-1 PR-review triage fix (`f17c36`, `cleanup.md`) wrote a verification instruction
that reproduced the same mistake one level up.

The instruction offered `claimed_count` as a **standalone alternative** to checking
`claimed[]` membership. CodeRabbit finding `c3ddfb` refuted it:

> a count rises by one whichever path was added, so a correction adding a different
> path passes the count with the required path still absent — the same wrong-surface
> comparison re-entering through the verification instrument.

The fix landed in the plan's final commit `e60da719c`: `cleanup.md:74` now requires
**membership primary, `claimed_count` secondary**.

## Why it matters

This is the third layer of one archetype in a single run:

1. the shipped gate compared a surface that could not express its own third state;
2. the self-review rounds closed a class against an instrument that could not reach
   every carrier;
3. the fix for (1) was verified by a count that cannot observe *which* member changed.

A cardinality is a lossy projection of a set. Any requirement phrased over
**identity** ("path P must be present", "carrier C must be corrected") is
undecidable from a size, because every wrong edit that preserves arity passes.

## Rule

When a check must confirm that a **specific** element is present, corrected or
removed, assert **membership**. A count may ride alongside as a cheap secondary
signal, never as the primary or as an accepted alternative.

Applies to: `claimed[]` vs `claimed_count`, `indeterminate[]` vs
`indeterminate_count`, `unreadable[]` vs a tally, and any review instruction that
offers "or check that the count changed" as an option.

## Sibling

The same run refuted two completeness claims about a semantic class (rounds 4-6) —
see the sibling candidate lesson on discharging completeness claims.
