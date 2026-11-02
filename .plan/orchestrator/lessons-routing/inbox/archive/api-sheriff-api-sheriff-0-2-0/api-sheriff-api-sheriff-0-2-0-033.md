envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T13:57:50Z

# Candidate lesson: outline deliverable labels a mixed footprint as documentation-only (plan-marshall:phase-3-outline (deliverable labeling))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-41-validator-asset-forwarding-anchor-rules (PR cuioss/API-Sheriff#489), source message 001.

Related: api-sheriff-api-sheriff-0-2-0-020 (the same integration-tests/src/main/docker/** paths resolve to no module, which is likely why the outline fell back to a documentation label).


Source record: Q-Gate finding `acf8be` (phase 3-outline, severity warning, resolution `accepted` in-run).

## Observation

Deliverable 4 of the outline declared `module: documentation`, `domain: documentation`, profile bucket
`documentation_only`, but three of its six affected files were
`integration-tests/src/main/docker/sheriff-config{,-passthrough-empty,-refresh}/gateway.yaml`. Those
resolve to the `integration-tests` module, sit in the `*/src/main/**` build-input class of `build.map`,
and CLAUDE.md names them gate-requiring (a mixed change is not documentation-only). The deliverable's
own verification already ran integration-tests Surefire wiring tests.

## Why it was accepted, not fixed

Label nit only: deliverables 1-3 touched Java, so the build gate ran regardless, and deliverable 4's
verification already exercised the integration-tests wiring tests. No behaviour impact in this run.

## Candidate rule (for orchestrator classification)

When a deliverable edits comments inside `src/main/**` config files (e.g. gateway.yaml fixtures under
`integration-tests/src/main/docker/`), label it by the owning module and a `mixed`/`config` bucket, never
`documentation_only`. In a plan where it is the ONLY deliverable, the docs-only label would let phase-4
route it as documentation and the build gate could be skipped for a gate-requiring footprint.

Recurrence risk: the config-extraction plans in this epic (V02-*) repeatedly touch gateway.yaml comment
references to validator class names; the mislabel is likely to recur. Low severity; may already be covered
by an existing outline-labeling lesson — orchestrator to dedup.
