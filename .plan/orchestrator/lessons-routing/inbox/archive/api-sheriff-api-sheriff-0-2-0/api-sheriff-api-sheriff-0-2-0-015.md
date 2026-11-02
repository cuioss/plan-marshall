envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-17T09:32:41Z

# Candidate lesson: repo-wide doc-sweep verification needs depends on every deliverable that owns a hit

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 006. Suggested route: plan-marshall (phase-3-outline deliverable dependency authoring).



**Signal:** Q-Gate finding dc1bab (3-outline, warning, resolved `taken_into_account`).

## What happened

Deliverable 5's verification was a repo-wide doc search. It required hits for `ResolvedRoute|RouteRuntime|RouteRuntimeAssembler|RouteRuntimeAssemblerTest` to appear only in `doc/adr/` and `doc/quality-report/`. But `doc/LogMessages.adoc` (the ApiSheriff-1 row) also hit, and that file is owned by deliverable 3. D5 declared `depends: 2` only, so a task order that ran D5 before D3 would fail D5's verification. The fix was `depends: 2,3`.

## Suggested corrective action

When a deliverable's verification is a repo-wide absence or containment search, the outline author should run the search, map each current hit to the deliverable that owns that file, and add every such deliverable to `depends`. The alternative is to narrow the criterion to the files the deliverable itself owns.
