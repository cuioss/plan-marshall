envelope_version=1
sender_type=plan
sender_id=plan-v02-12-idp-addressing-model
epic=lessons-routing
kind=candidate-lesson
created=2026-10-20T20:29:31Z

# Candidate lesson: B7 no-progress predicate fires on legitimate orchestrator-tier build hand-backs (plan-marshall:phase-5-execute dispatch boundary)

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-12-idp-addressing-model (PR cuioss/API-Sheriff#492), lessons-capture step.

## Observation

When a dispatched leaf correctly handed a long-running build back to the orchestrator (the `execution_tier: orchestrator` contract: a leaf must not run the build itself), the dispatch-boundary B7 no-progress predicate classified the return as no progress and reclassified the voluntary checkpoint to an error. These reclassifications count into the run's script-failure clusters.

## Why it matters

The leaf did exactly what the contract requires. Penalising the sanctioned hand-back pushes agents toward running orchestrator-tier builds inside the leaf, and it inflates the failure-cluster signal with false positives (this run: 9 clusters, several of them hand-backs).

## Suggested direction

Exempt a return whose payload is a declared orchestrator-tier build hand-back (or any declared hand-back signal) from the no-progress predicate, or count the hand-back as progress when the orchestrator's subsequent build succeeds.
