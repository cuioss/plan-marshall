envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:50Z

# Candidate lesson: misplaced `--plan-id` on `architecture search --content --pattern`

- Source: script-failure cluster (work-log failure marker)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Failing notation: plan-marshall:manage-architecture:architecture
- Candidate component: plan-marshall:manage-architecture

## Observation

An agent ran `architecture search --content --pattern P` with `--plan-id` in a position the parser does not accept for this verb, and argparse rejected the call. This matches the verb-scoped / router-scoped `--plan-id` placement signature from persona-plan-marshall-agent "Never invent script subcommands — recurrence signatures". The execution-context contract already says `--plan-id` is forwarded only where the script's own parser declares it, and only in the position that parser requires.

This verb is the first-choice content-search fallback for dispatched leaves that are denied Grep. A rejection here costs a retry on a path that every leaf is told to use first.

## Possible rule (for orchestrator judgement)

Before adding `--plan-id` to an `architecture search` call, check where the manage-architecture client-api / canonical-invocations block places it (or whether the verb declares it at all). If not, append nothing. The search verb's canonical block could state its `--plan-id` position explicitly, since leaves reach for this verb first.
