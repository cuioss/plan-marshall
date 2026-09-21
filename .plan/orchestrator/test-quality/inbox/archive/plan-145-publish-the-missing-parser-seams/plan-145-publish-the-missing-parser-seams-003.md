envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:25Z

# A deliverable can state three mutually inconsistent things about one roster, and the inconsistency deletes half the guard

**Signal**: Q-Gate finding (`3-outline`, hash `21aba3`, severity `error`, resolution `taken_into_account`)
**Component**: `plan-marshall:phase-3-outline`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## What was observed

Deliverable 1 said three things that could not all hold:

1. Change-per-file item 2 probed "every population member that is **not** on `SEAM_EXEMPT`".
2. Item 3 then asserted "the set that raised `ParserSeamNotFound` is **exactly** `SEAM_EXEMPT`".
3. The Risks table resolved probe scope the same way as item 2.

Under item 2's probe scope the raising set is necessarily EMPTY, never `SEAM_EXEMPT`, so item 3 could not hold as written — and the Success Criteria clause "and equally when a `SEAM_EXEMPT` row stops raising" was therefore unimplementable.

The deeper consequence: the seam contract resolves TWO seams (a published zero-arg builder, and interception of `argparse.ArgumentParser.parse_args` inside `main()`). A structural "publishes no zero-arg builder" pin covers seam 1 only, so an exempt row that later acquires a seam-2 path stays green forever and the exempt roster goes stale undetected.

## Why it is candidate-lesson material

Three sections of one deliverable each described the guard correctly in isolation; only reading them **against each other** exposed that the staleness direction — the half that keeps a recorded verdict honest over time — had been specified out of existence. Nothing in the authoring flow forces that cross-section reconciliation.

## Proposed rule (for orchestrator judgement)

Where a deliverable asserts set equality against a roster, require the assertion's **probe scope** to be stated once and referenced, not restated per section. A guard specified as "assert X equals the roster" while the probe excludes the roster is a detectable contradiction: the asserted set is provably empty under the stated scope.

## Related already-active lessons

- `2026-09-03-06-006` — admitting a file to scope is not admitting its mirrored sites
- `2026-09-03-07-005` — a success criterion must be operationalizable from the outline alone
