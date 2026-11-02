envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T13:55:56Z

# Candidate lesson: module_mapping_validator false positive: integration-tests/src/main/docker is outside the architecture inventory (plan-marshall:phase-4-plan module_mapping_validator / manage-architecture)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-40-validator-terminal-edge-protocol-rules (PR cuioss/API-Sheriff#485), source message 003.


**Source**: 4-plan Q-Gate, finding b19128 (module_mapping_validator, accepted).
**Probable owner**: plan-marshall:manage-architecture (inventory coverage) / plan-marshall:phase-4-plan module_mapping_validator. Project angle: the API-Sheriff architecture inventory.

## What happened

TASK-7 (implementation) targets `integration-tests/src/main/docker/sheriff-config/topology.properties` and `.../endpoints/assets.yaml`. For both, `architecture which-module` returns `module: null`, because `src/main/docker/**` is not in the crawled inventory. The validator therefore compared `integration-tests` (TASK-8) against `unresolved` (TASK-7) and reported a test/impl module mismatch. It also pointed to `doc/developer/test-impl-mapping.adoc`, a file this project does not have. All four files live under `integration-tests/`, so the finding was accepted as an inventory gap.

## Corrective rule (candidate)

The module_mapping validator should treat `module: null` as "could not check", not as a mismatch. It could also fall back to the longest module-root prefix of the path. Separately, the API-Sheriff inventory could attribute `*/src/main/docker/**` to the module that contains it, because docker config under integration-tests is routine plan surface here (topology, endpoint yaml, compose files).
