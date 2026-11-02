envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T06:22:28Z

# Candidate lesson: a moved test that reads a constant a later deliverable also moves was not owned by that later deliverable (plan-marshall:phase-3-outline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-25-edge-route-decomposition (PR cuioss/API-Sheriff#487), source message 002.


- Source: Q-Gate finding d81168 (phase 3-outline, resolution: taken_into_account)
- Plan: plan-v02-25-edge-route-decomposition (V02-25, edge route decomposition)

### Observation

Deliverable 1 moved `EdgeHardeningTest` into `edge/admission/`. That test reads `GatewayEdgeRoute.UPSTREAM_TIMEOUT_SECONDS` in code, and deliverable 2 moves that constant to `upstream.UpstreamGuards`. Deliverable 2's affected files listed only `GatewayEdgeRouteTest` and `GatewayEdgeRouteRetryAfterTest`, so the moved test would have stopped compiling at deliverable 2's verification. The `GatewayEdgeRouteTest` retarget list also missed `COOKIE_HEADER_OVERHEAD_BYTES`, `ADMISSION_GUARD_KEY` and three `relayOnEventLoop` calls.

### Resolution in run

The outline added the test (write-replace, post-D1 path) to deliverable 2, widened the retarget list from an architecture search over tests for `GatewayEdgeRoute.<member>` with retained members excluded, and added a D2 success criterion: no non-comment test line names a moved `GatewayEdgeRoute` member. The re-run sweep returned zero files.

### Candidate rule (for orchestrator classification)

In a multi-deliverable move/split, derive each deliverable's consumer set from a sweep over the tree as it stands AFTER the earlier deliverables, not over HEAD. A file one deliverable relocates can still read members a later deliverable moves. Express the success criterion as a zero-residual sweep so the outline is checked against the sweep result.
