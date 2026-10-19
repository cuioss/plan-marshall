envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:50Z

# Candidate lesson: invented verb `qgate query` on manage-findings

- Source: script-failure cluster (work-log failure marker)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Failing notation: plan-marshall:manage-findings:manage-findings
- Candidate component: plan-marshall:manage-findings

## Observation

An agent called `manage-findings qgate query ...`. The `qgate` noun has no `query` sub-verb; the read verb is `qgate list` (with `--plan-id`, `--phase`, and `--resolution` filters). argparse rejected the call with exit 2. This is the verb-paraphrase signature from persona-plan-marshall-agent "Never invent script subcommands — recurrence signatures".

## Possible rule (for orchestrator judgement)

Quote the `qgate` read verb verbatim from the manage-findings canonical invocations (`qgate list`), never a synonym (`query`, `get`, `read`). If this recurs across plans, an accepted alias or a "did you mean `list`" hint in the argparse error could cut the retry cost.
