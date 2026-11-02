envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-18T06:22:28Z

# Candidate lesson: deep-lane outline Q-Gate flagged zero CERTAIN_INCLUDE assessments (plan-marshall:phase-3-outline / manage-findings)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-25-edge-route-decomposition (PR cuioss/API-Sheriff#487), source message 001.

RECURRENCE (third plan in this epic): same class as api-sheriff-api-sheriff-0-2-0-014 and -019, archived pm-mcp-core-m2-m4-238.


- Source: Q-Gate finding 4ebe57 (phase 3-outline, resolution: accepted)
- Plan: plan-v02-25-edge-route-decomposition (V02-25, edge route decomposition)

### Observation

The 3-outline Q-Gate reported that `manage-findings assessment list --certainty CERTAIN_INCLUDE` returned zero records (findings_store_state: missing) for a deep-lane plan, so the Step 5 missing-coverage check had no assessed set to compare the declared affected files against.

### Resolution in run

Accepted with deterministic `architecture search --content` consumer sweeps recorded in the outline as the substitute evidence (importers of `sheriff.gateway.edge.*`, nested-type sweeps, `GatewayEdgeRoute.<member>` sweeps). The q-gate re-ran those sweeps and they agreed with the declared files except for two scope findings (d81168, c88682). Writing ~160 per-file assessment records was judged to duplicate the sweep evidence.

### Candidate rule (for orchestrator classification)

For a sweep-driven refactor outline, either record component assessments from the discovery step, or state the sweep commands and their results in the outline so the coverage check can be accepted against them. The coverage check silently has nothing to compare against when neither is present.
