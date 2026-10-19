envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-19T17:28:50Z

# Candidate lesson: `--number` used instead of `--deliverable-number` on manage-solution-outline (twice)

- Source: script-failure cluster (work-log failure marker, 2 occurrences)
- Plan: plan-37-ported-primitive-tests (pm-mcp-core)
- Failing notation: plan-marshall:manage-solution-outline:manage-solution-outline
- Candidate component: plan-marshall:manage-solution-outline

## Observation

An agent addressed a deliverable with `--number N`. manage-solution-outline declares the typed-ID flag `--deliverable-number`, so argparse rejected both calls with exit 2. The same mistake happened twice in one plan, so the first rejection did not prevent the second. This is a typed-ID naming slip, a close relative of the verb-paraphrase signature (see persona-plan-marshall-agent standards/argument-naming.md, typed-ID flags).

## Possible rule (for orchestrator judgement)

Always take the deliverable selector verbatim from the manage-solution-outline canonical invocations: `--deliverable-number`, never the bare `--number`. Because it recurred within one plan, the argparse error could name the canonical flag, or `--number` could be reviewed as a candidate for the accepted-alias carve-out.
