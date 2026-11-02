envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=candidate-lesson
created=2026-10-15T15:42:28Z

# Candidate lesson: architecture search called with --plan-id after the verb (plan-marshall:manage-architecture)

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-26-config-validator-split` (PR cuioss/API-Sheriff#463), source message 004 (previously filed locally as API-Sheriff lesson 2026-10-14-20-002, now removed there).


**Source signal:** script-failure cluster (1 distinct notation): `plan-marshall:manage-architecture:architecture search`.

**Observation:** During finalize (2026-10-14T18:59:23Z) the call

`architecture search --content --pattern endpointFile\( --plan-id plan-v02-26-config-validator-split`

failed with exit 2, `error: misplaced_router_flag`. `--plan-id` is a top-level router flag on `architecture.py` and must precede the subcommand (`architecture --plan-id {plan_id} search --content --pattern ...`). The retry in the correct position succeeded seconds later, so the cost was one wasted call, but this is the known router-scoped flag recurrence signature (the mirror of the verb-scoped `--plan-id` case).

**Candidate corrective direction (for orchestrator classification):** Agents appending `--plan-id` by rote after the verb is the recurring cause; the per-script canonical invocation block for `architecture` should be consulted before adding `--plan-id`. The script's own error already names the fix, so this is an agent-discipline recurrence rather than a script defect.

**Suggested component:** plan-marshall:manage-architecture
