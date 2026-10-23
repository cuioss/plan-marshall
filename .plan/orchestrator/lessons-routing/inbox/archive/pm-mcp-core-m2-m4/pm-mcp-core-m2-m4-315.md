envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:56:31Z

component=plan-marshall:manage-findings
category=anti-pattern
source=script-failure cluster, work log c3533b (2026-10-17T15:15:07Z, phase-3-outline re-dispatch)

# Invented verb `qgate query` on manage-findings

## Observation

During the phase-3-outline re-dispatch, an agent called `manage-findings qgate query`, which was rejected with argparse_rejection exit 2. The registered `qgate` verbs are add, clear, list, resolve, resolve-by-rule and resolve-evidenced.

## Rule

Use `qgate list --plan-id P --phase X` to read Q-Gate findings. This is the verb-paraphrase recurrence signature. Check whether a phase-3-outline workflow passage reads "query the Q-Gate findings" in a way that invites the invented verb.
