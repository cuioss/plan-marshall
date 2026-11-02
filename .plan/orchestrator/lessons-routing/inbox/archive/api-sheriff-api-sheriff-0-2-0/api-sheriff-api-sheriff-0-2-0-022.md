envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-17T13:55:57Z

# Candidate lesson: pre-push-quality-gate resolves zero bundles for a Maven reactor; module-tests has no root canonical (plan-marshall:phase-6-finalize pre-push-quality-gate)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-40-validator-terminal-edge-protocol-rules (PR cuioss/API-Sheriff#485), source message 005.

RECURRENCE: same class as api-sheriff-api-sheriff-0-2-0-005 and archived pm-mcp-core-m2-m4-043/104/205/216/229/237/267.


**Source**: finalize work log, 2026-10-17T12:17:57Z WARNING from plan-marshall:pre-push-quality-gate, plus orchestrator observation.
**Probable owner**: plan-marshall:phase-6-finalize pre-push-quality-gate (`derive_gate_bundles`) / plan-marshall:build-maven canonical command set. Not a project defect.

## What happened

The gate logged: "Footprint paths matched a build_map glob but resolved to no bundle: 15 api-sheriff/integration-tests Java paths (derive_gate_bundles is marketplace-bundle-shaped; Maven modules are not bundles) — proceeding; these are gated by the whole-tree quality-gate arm instead of per bundle." `derive_gate_bundles` maps footprint paths to `marketplace/bundles/{bundle}` and finds nothing in a Maven reactor. In Maven, `module-tests` has no root-level canonical either. So the documented per-module test arm does not run, and only the whole-tree quality gate covers the change, unless full `verify` is run as well.

## Corrective rule (candidate)

`derive_gate_bundles` should derive gate units from the active build system's module inventory (Maven modules via `architecture which-module`), not from the marketplace bundle layout. Failing that, when it resolves zero units for a non-empty build-relevant footprint, it should fall back to an explicit root `verify` rather than quietly narrowing to the quality-gate arm. Until then, API-Sheriff plans should run the full `verify` (or `test -pl <module> -am`) by hand at the gate. That matches the project memory note that the pre-commit gate runs only about 200 tests.
