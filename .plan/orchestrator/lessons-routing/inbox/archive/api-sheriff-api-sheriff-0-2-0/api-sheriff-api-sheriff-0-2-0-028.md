envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T06:22:29Z

# Candidate lesson: an "outside files earlier deliverables edit" sweep exclusion left comment references unowned (plan-marshall:phase-3-outline)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-25-edge-route-decomposition (PR cuioss/API-Sheriff#487), source message 003.


- Source: Q-Gate finding c88682 (phase 3-outline, resolution: taken_into_account)
- Plan: plan-v02-25-edge-route-decomposition (V02-25, edge route decomposition)

### Observation

Deliverable 3 (comment/Javadoc cleanup of moved `GatewayEdgeRoute` members) excluded files that deliverables 1-2 already edit. D1 restricts its edits to package lines and imports, so the exclusion left comment references to moved members unowned: `GatewayEdgeErrorPageTest:112` (`{@code GatewayEdgeRoute.guardFor}`), `DispatchStageTest`, `ReservedBodyCeilingTest`. The exclusion was also applied unevenly: D1-edited main classes were surveyed, D1-edited tests were not.

### Resolution in run

The exclusion was dropped and replaced with an ownership rule: D2 fixes moved-member references (code or comment) only in the files it rewrites, D3 owns every other comment reference, D1-moved files included. The sweep found 11 Java files, all now owned. The same rule applied to docs moved three adoc files to D5.

### Candidate rule (for orchestrator classification)

Do not scope a cleanup deliverable by "files another deliverable already touches". Touching a file is not owning every reference in it. Assign ownership by what each deliverable actually changes in a file (for example, imports only versus a full rewrite), and check that the union of ownership covers the whole sweep result.
