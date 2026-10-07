envelope_version=1
sender_type=plan
sender_id=fail-closed-signal-integrity
epic=truthful-signals
kind=candidate-lesson
created=2026-08-02T21:11:11Z

component=plan-marshall:phase-3-outline
category=anti-pattern
bundle=plan-marshall

# The consumer-sweep archetype recurred twice in one plan — a declared consumer count is a SAMPLE

Two independent recurrences of the same archetype inside a single plan:

1. **The outline declared 1 consumer of the changed signature; there were 2.** The declared
   count was an artefact of how far the author looked, presented as the size of the set.
2. **A roster's population was a strict subset of its own predicate's domain.** The detector
   guarded a set smaller than the set it claimed to guard, so the members outside the roster
   were unguarded and the guard still reported clean.

Both are the standing archetype: *a list of call sites produced by looking is a sample, not
an enumeration.* Two more instances now, on top of the previously-logged recurrences.

## Impact

In this run the archetype was caught before shipping, but only because a later pass
re-derived the population instead of trusting the earlier count. A single-pass plan would
have shipped a change that missed a live consumer with a confident "1 consumer updated"
claim attached.

Directly sizes the OWED epic follow-up: enforcing a single authoritative `_TEST_ROOTS`
(remedy B — thread the root set through `resolve_test_scope`) touches exactly this
signature, so that work must be sized against the consumer-sweep hazard rather than against
a hand-counted consumer list.

## Solution

- Never state a consumer count that was produced by looking. Derive it from the population
  (structured architecture query over the signature) and state the query, so the claim is
  reproducible and its failure mode is visible.
- Every set-guarding detector must be **population-derived** — the roster is computed from
  the predicate's domain, never hand-listed alongside it. `test/_shared/_dispatch_roster.py`
  is the in-repo pattern to copy.
- When a fix WIDENS the population, re-check the detector's anchor: a
  population-derived detector built against the old, narrower domain is silently wrong
  against the new one.
