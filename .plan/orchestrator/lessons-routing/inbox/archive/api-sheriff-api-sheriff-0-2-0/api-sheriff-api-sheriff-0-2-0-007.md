envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T15:42:31Z

# Candidate lesson: light-lane router under-read a spec-pointer request and escalated (plan-marshall:phase-1-init (lane routing) / plan-marshall:phase-3-outline)

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-26-config-validator-split` (PR cuioss/API-Sheriff#463), source message 005 (previously filed locally as API-Sheriff lesson 2026-10-14-20-003, now removed there).


**Source signal:** orchestrator-observed run behaviour (planning-lane routing).

**Observation:** The plan was launched from a staged epic spec (request = pointer to the PLAN spec for the ConfigValidator split). The light-lane scope heuristic counted only the 2 paths visible in the request text itself, not the surface the pointed-to spec declares in its `## Expected Surface` (the actual change touched 17 files across main code, tests and docs). The router therefore initially judged the change light and then had to escalate to the deep lane once the real scope surfaced.

**Why it matters:** An orchestrated request is typically a short pointer; its scope lives in the spec, so a path count over the request text systematically under-reads it, and the escalation costs a routing round-trip.

**Candidate corrective direction (for orchestrator classification):** When the request `source_id` resolves to an orchestrator plan spec, the lane router should derive its scope signal from that spec's declared surface (`orchestrator corpus surfaces`) rather than from paths mentioned in the request narrative.

**Suggested component:** plan-marshall:phase-1-init (lane routing) / plan-marshall:phase-3-outline
