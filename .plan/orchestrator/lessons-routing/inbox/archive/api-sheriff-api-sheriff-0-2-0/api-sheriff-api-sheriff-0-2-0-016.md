envelope_version=1
sender_type=orchestrator
sender_id=api-sheriff-api-sheriff-0-2-0
epic=lessons-routing
kind=finding
created=2026-10-17T09:32:41Z

# Candidate lesson: invented `--number` flag on manage-solution-outline get-deliverable

Forwarded from API-Sheriff epic `api-sheriff-0-2-0`, plan `plan-v02-44-route-type-merge` (PR cuioss/API-Sheriff#476), source message 008. Suggested route: plan-marshall (argparse-rejection recurrence, verb-flag paraphrase).

RECURRENCE of the plausible-flag-paraphrase / argparse-rejection class (e.g. api-sheriff-kidicap-gateway-requirements-010 in this inbox's archive).



**Signal:** script failure, work-log row 6a94f5 (2026-10-15T16:58:50Z).

## What happened

```
script_failure notation=plan-marshall:manage-solution-outline:manage-solution-outline exit_code=2
failure_kind=argparse_rejection detail=`--number` is not declared for
`plan-marshall:manage-solution-outline:manage-solution-outline get-deliverable`: ['deliverable-number', 'plan-id']
```

A phase-5-execute leaf, in its per-deliverable commit step, called `get-deliverable --number N` instead of `--deliverable-number N`. It recovered, but this is the "plausible-flag paraphrase" class the persona's "Never invent script subcommands" rule targets.

## Suggested corrective action

Check that every phase-5-execute or execute-task workflow site calling `get-deliverable` quotes `--deliverable-number` verbatim from the canonical-invocation block. If a doc site shows `--number`, fix it.
