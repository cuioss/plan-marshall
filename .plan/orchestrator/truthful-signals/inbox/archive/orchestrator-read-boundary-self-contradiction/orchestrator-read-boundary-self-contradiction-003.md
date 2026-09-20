envelope_version=1
sender_type=plan
sender_id=orchestrator-read-boundary-self-contradiction
epic=truthful-signals
kind=candidate-lesson
created=2026-07-28T20:09:08Z

component=plan-marshall:phase-3-outline
category=anti-pattern
created=2026-07-28
bundle=plan-marshall

# A regression detector's population must not be narrower than the fix set's population

## What happened

Q-Gate finding `3985e9` at `3-outline`, escalated to operator resolution `137ac5`.

Deliverable 3 of PR #1040 specified a "population-derived detector" enumerating every
`*.md` under `MARKETPLACE_ROOT` (= `marketplace/bundles`). Deliverable 2's declared
survey scope was strictly wider: marketplace `*.md` **plus** `doc/**/*.adoc` **plus**
`CLAUDE.md`. And the one live uncorrected restatement the sweep actually found sat at
`doc/concepts/orchestration.adoc:31` — inside the gap.

The result: a regression guard that was **structurally incapable of failing on the one
surface where the real hit was found**. It would have shipped green while a concept doc
still stated the prohibition the plan had just deleted, and any future reintroduction in
`doc/` or `CLAUDE.md` would have been equally invisible to it.

## Solution

**Rule:** when a plan (a) sweeps a surface for a contradiction and (b) adds a regression
detector for it, assert `detector_population ⊇ fix_set_population` explicitly at outline
time. State it as a normative line in the deliverable, not as an implicit consequence of
the chosen root constant.

Operationally, for this plan:

- widen the detector population to the exact union D2 sweeps (marketplace `*.md`
  ∪ `PROJECT_ROOT/doc/**/*.adoc` ∪ `CLAUDE.md`);
- extend sentence extraction to handle the **AsciiDoc surface forms**, or a
  Markdown-shaped tokenizer silently skips every `.adoc` hit and you are back to a
  vacuous population with a wider-looking glob;
- add a **positive-population guard**: assert each surface slice is non-empty *and* that
  the known-hit file is present in the enumerated population.

That last point is the load-bearing one. Without it, widening the glob is unverified —
a glob that matches nothing looks identical to a glob that matches everything correct.

## Impact

**Two independent vacuity axes, not one.** The existing anti-vacuity practice is the
negative fixture: feed the detector the pre-fix sentence and assert it is flagged. That
proves the detector **fires**. It does not prove the **population** it scans contains the
documents at risk. Both need a guard, and the population axis is the one that is
routinely missed because the fixture test passing feels like sufficient proof of
non-vacuity.

| Axis | Question | Guard |
|------|----------|-------|
| Predicate | Does the detector flag the bad content? | Negative fixture carrying the pre-fix text verbatim |
| Population | Does the scanned set contain the at-risk documents? | Positive-population assertion: slice non-empty **and** contains the known hit |

**Extends the existing rule, does not replace it.** "Every set-guarding detector must be
population-derived" (i.e. derived from the source set rather than hardcoded) is already
recorded. This adds the *relation to the fix set*: population-derived is not enough if
the source set you derive from is the wrong, narrower one. Derive from the set the plan
actually corrected.

**Generalization for `phase-3-outline`:** whenever a deliverable declares a survey scope
and a sibling deliverable adds the guard, the outline validator should compare the two
scopes and raise when the guard's is narrower. This was caught by an LLM Q-Gate pass here;
it is a mechanical comparison and could be a deterministic check.
