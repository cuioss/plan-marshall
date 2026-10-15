envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-kidicap-gateway-requirements
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T12:24:58Z

# Candidate lesson: build-server jobs reported `job_status=timeout` under foreign machine load (clipped, not hung) (build-server-client)

Forwarded from API-Sheriff epic `kidicap-gateway-requirements`, plan `plan-32-early-answer-it-timeouts` (PR cuioss/API-Sheriff#466).

Source message: 028 (build-server waits: job c880840d at 2026-10-14T20:54:17Z and job e4e96909 at 2026-10-15T08:28:19Z, each followed by a green re-run with no code change).

## Observation

Two long Maven runs through the build server ended `job_status=timeout` while other work loaded the machine. A re-submission succeeded. The same pattern is known for direct gate runs.

## Candidate rule

Read a build-server `timeout` first as "clipped by the time limit": check machine load and the Maven log tail, then re-submit once before blaming the change. Consider surfacing load or elapsed-versus-budget in the timeout payload so the reading is not a judgement call.
