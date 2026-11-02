envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-18T06:22:29Z

# Candidate lesson: invented manage-findings verb `query` (plan-marshall:manage-findings (verb paraphrase))

Forwarded from API-Sheriff epic api-sheriff-0-2-0, plan plan-v02-25-edge-route-decomposition (PR cuioss/API-Sheriff#487), source message 007.

RECURRENCE: invented-verb/flag paraphrase class, as api-sheriff-api-sheriff-0-2-0-016.


- Source: script-failure cluster, notation plan-marshall:manage-findings:manage-findings
- Plan: plan-v02-25-edge-route-decomposition (V02-25, edge route decomposition)

### Observation

During the run an agent called `manage-findings query`. The script has no `query` verb, so argparse rejected the call. The correct verb for reading plan findings is `list` (for example `manage-findings list --plan-id P --type pr-comment --resolution fixed`, or `manage-findings qgate list --plan-id P --phase PHASE`).

### Candidate rule (for orchestrator classification)

This is the verb-paraphrase signature of "never invent script subcommands": `query` is plausible because `manage-change-ledger` really has a `query` verb, so the name crosses over between sibling manage-* scripts. Take verbs from the script's canonical-invocation block, not from a sibling script.
