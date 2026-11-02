envelope_version=1
sender_type=orchestrator
sender_id=lessons-routing
epic=lessons-routing
kind=finding
created=2026-10-27T17:51:17Z

# Outline and plan validators: a consumer sweep that skips test sources, missing dependency edges, and two false positives

Source: API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-05-response-hygiene (PR #526), candidate lessons 006, 009 and 010. Observed with plugin and executor 0.1.2010.

## Observation

1. The first outline pass claimed its consumer sweep enumerated every caller of a changed signature, but missed three test-source call sites: two positional calls of a record's canonical constructor after a record component was added, and calls of a method that gained a parameter. Three Q-Gate records.
2. A deliverable added cross-references into content that only another deliverable creates, yet declared no dependency on it, so task order could run it first and fail its own "every added cross-reference resolves" criterion. The orchestrator patched it in phase-4-plan.
3. `module_mapping_validator` flagged correct pairings twice: a documentation target in an implementation task whose code targets all resolve to the test module's module, and IT stack configuration under `integration-tests/src/main/docker/**`, which the architecture inventory attributes to no module. The suggested escape hatch file does not exist in this repository.

## What to consider

- For any record-component or method-signature change, run the consumer sweep per changed symbol over the full inventory including test sources, and make every hit an explicit change entry.
- Derive deliverable dependencies from the change entries (new anchors versus new xrefs) instead of relying on the author.
- Ignore documentation-module targets in the test/implementation pairing check, and attribute files physically under a module directory to that module.
