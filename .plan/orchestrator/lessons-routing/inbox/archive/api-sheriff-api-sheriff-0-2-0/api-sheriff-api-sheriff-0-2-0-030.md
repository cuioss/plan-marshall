envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-18T06:22:30Z

# Candidate lesson: undeclared `--number` flag passed to manage-solution-outline (plan-marshall:manage-solution-outline (flag paraphrase))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-25-edge-route-decomposition (PR cuioss/API-Sheriff#487), source message 008.

RECURRENCE: the same invented `--number` flag as api-sheriff-api-sheriff-0-2-0-016 (PLAN-V02-44).


- Source: script-failure cluster, notation plan-marshall:manage-solution-outline:manage-solution-outline
- Plan: plan-v02-25-edge-route-decomposition (V02-25, edge route decomposition)

### Observation

An agent passed `--number` to a `manage-solution-outline` verb. The flag is not declared, so argparse rejected the call as an unrecognized argument.

### Candidate rule (for orchestrator classification)

This is the typed-ID flag case of "never invent script arguments": a generic `--number` was guessed instead of the typed flag the verb declares. Check the verb's canonical-invocation block or `--help` for the deliverable-addressing flag before calling, and do not carry flag names over from `manage-tasks` (`--task-number`) or other siblings.
