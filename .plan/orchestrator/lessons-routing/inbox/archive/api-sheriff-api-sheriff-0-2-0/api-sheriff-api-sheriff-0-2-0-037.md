envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-21T12:52:14Z

# Candidate lesson: derive_gate_bundles resolves no bundle for a Maven reactor; no default-scope module-tests canonical (plan-marshall:phase-6-finalize pre-push-quality-gate)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-42-validator-auth-oidc-rules (PR cuioss/API-Sheriff#502), source message 002.

RECURRENCE: same class as api-sheriff-api-sheriff-0-2-0-005 and -022 (and archived pm-mcp-core-m2-m4-043/104/205/216/229/237/267). Third API-Sheriff occurrence.

**Routing:** plan-marshall tooling candidate. Send it to the plan-marshall lessons-routing inbox, not to the local store.
**Suggested component:** plan-marshall:phase-6-finalize (pre-push-quality-gate / derive_gate_bundles) and plan-marshall:manage-architecture (resolve)
**Category:** bug
**Source:** orchestrator observation during PLAN-V02-42 finalize. The drain should verify it against the plan work log.

## What happened

On API-Sheriff, a multi-module Maven reactor with no marketplace bundles, `derive_gate_bundles`
reported every Java module path as `unresolved`. That function backs the pre-push-quality-gate
step and reads the footprint per bundle. Separately, `architecture resolve` had no
test-compile or module-tests canonical command at the default scope. The arms of the gate
document assume a pyprojectx / marketplace-bundle layout, so they did not map cleanly onto a
Maven project. The orchestrator had to work out the correct Maven gate command by hand.

## Corrective action

derive_gate_bundles should fall back to module resolution through the architecture inventory
(`which-module`) when the project has no bundles. It should not return the whole footprint as
`unresolved`. `architecture resolve` should expose a test-compile/module-tests canonical at
default scope for Maven, or the gate document should name its Maven arm explicitly.
