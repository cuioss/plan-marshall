envelope_version=1
sender_type=plan
sender_id=plan-145-publish-the-missing-parser-seams
epic=test-quality
kind=candidate-lesson
created=2026-09-04T14:48:38Z

# Drift computed in both directions but only printed: a green session tolerates a drifted roster

**Signal**: automated review — CodeRabbit inline finding `4fa036`, severity Minor, triaged FIX and fixed in-run
**Component**: `plan-marshall:persona-module-tester` (test-guard authoring) — surfaced in `test/conftest.py:999`
**Plan**: `plan-145-publish-the-missing-parser-seams` (PR #1395, merged `8d8c17bd`)

## What the reviewer said

> `_ROUTING_GUARD_MODULES` duplicates membership that `_discover_guard_publishers` derives from `GUARD_POPULATION_LABEL`. `_guard_roster` only **reports** drift, so a green session does not enforce a matching roster.

## What was confirmed, and the one correction

Half the claim was already handled: `_guard_roster` appends every discovered publisher with no `_ROUTING_GUARD_MODULES` row as an `UNLISTED` entry, so the tuple supplied order and short names only — already the derived shape the reviewer prescribed.

The residual was the reviewer's **second** point, and it was real: drift was computed in both directions but only **printed**, so a session could go green over a drifted roster. Fixed with a collected test asserting `_guard_roster` reports no discrepancies (non-empty population asserted first, both drift directions covered by positive controls) — deliberately **not** by raising from `pytest_report_header`, since that hook runs pre-collection and raising there turns a roster defect into a startup error naming neither the test nor the cause.

## Why it is candidate-lesson material

The failure mode is "the check exists and computes the right answer, and nothing consumes it." A reported-not-asserted diagnostic is strictly worse than an absent one: it manufactures the appearance of coverage. This is the same family as the project's standing rule that a guard which could not look must not render as a guard that passed.

## Proposed rule (for orchestrator judgement)

A drift/parity computation must terminate in an **assertion**, not a print. Where the natural site is a pre-collection hook, move the assertion into a collected test rather than raising from the hook — a startup error that names neither the test nor the cause is not a usable failure.
