envelope_version=1
sender_type=orchestrator
sender_id=libraries-initial-implementation
epic=lessons-routing
kind=candidate-lesson
created=2026-11-24T12:07:27Z

component=plan-marshall:phase-3-outline
category=improvement
title=phase-3-outline: walk every never / must-not clause of a specification section and map each to a check and a test case
source_lesson=2026-11-20-14-002
source_repo=git-document-repository (epic libraries-initial-implementation)
source_created=2026-11-20

# phase-3-outline: walk every never / must-not clause of a specification section and map each to a check and a test case

# Candidate lesson: an outline left a specified refusal without a check, because it mapped keys and presence rules but not the section's negative clauses

- Source signal: plan plan-07-store-module-registry-spi (inbox plan-07-store-module-registry-spi-002), Q-Gate finding 293efd (phase 3-outline, severity warning, resolution `taken_into_account`).

## What happened

`doc/specification/git-store.adoc` § Configuration defines `anchor.signed.key-source` and `anchor.signed.key` as "the anchor key of signed; never the commit-signing key". Deliverable 4 typed and validated every present key of the section but named no start check that refuses an anchor key equal to the signing key. The Q-Gate caught it. Deliverable 4 then gained the refusal (a `MALFORMED` outcome naming `anchor.signed.key`, never the value), with `StoreConfigurationTest` cases and a success criterion.

## Candidate rule

When a deliverable implements a specification section, walk every "never" / "must not" clause of that section and map each to a check and a test case in the deliverable, not only the key typing and presence rules. A specification carries negative constraints that key-by-key validation misses.
