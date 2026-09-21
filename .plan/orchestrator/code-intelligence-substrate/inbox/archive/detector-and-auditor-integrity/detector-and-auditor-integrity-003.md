envelope_version=1
sender_type=plan
sender_id=detector-and-auditor-integrity
epic=code-intelligence-substrate
kind=candidate-lesson
created=2026-08-31T08:29:49Z

# The Executive Summary section can never be written on the documented workflow path

component: plan-marshall:plan-retrospective
category: bug
severity: error
source_plan: detector-and-auditor-integrity
source_pr: 1370

## What was observed

`compile-report run` on this plan returned `sections_written[17]` and placed
**Executive Summary** in `sections_omitted` — the BENIGN half of the partition,
the half that means "the trigger fragment was absent or carried nothing
renderable, so there was nothing to lose". The report carries 8 error-severity
findings and no headline section.

## Why it cannot fire

Three facts compose:

1. `build_document` renders the section **only** from a `_executive-summary`
   fragment already present in the bundle: `fragments.get('_executive-summary')`,
   used verbatim. It synthesizes nothing.
2. `retro_sections` states the underscore prefix means "`compile-report` computes
   and injects this record itself, so — exactly like `_executive-summary` — it
   must never be registerable through `collect-fragments add`". `valid_aspect_keys`
   filters underscore-prefixed keys, so **no producer may register it**.
3. No injection site was found. All 4 occurrences in `compile-report.py` are
   reads/comparisons; 15 of the 18 occurrences across the corpus are in TESTS,
   where fixtures supply the key.

So the consumer never computes it and the producer may never register it. The
only writer in the repository is a test fixture.

## Why the existing verification did not catch it

The drop-versus-omit predicate (`_exec_summary_is_drop`) is well tested — because
the fixtures inject `_executive-summary` directly. Under those fixtures the
section renders and the predicate is exercised on the populated path. In
production the key is always absent, `_exec_summary_is_drop` returns False for a
non-dict, and the section takes the quiet `omitted` branch every time. This plan
ran 4 self-review rounds and killed 42/42 mutants without surfacing it: the
mutation population is the code the fixtures reach.

## The generalizable rule

A section whose only production writer is a test fixture is a section that never
renders. When a key is structurally unregisterable by producers, the consumer
MUST be the one that computes it — and a test that supplies the key by hand is
testing the renderer, not the pipeline. Assert the production path end to end:
run the documented workflow and assert the heading is in `sections_written`.
