envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T09:16:37Z

# Candidate lesson: manage-solution-outline verb/flag paraphrases (deliverable-hashes, --number)

Source: script-failure cluster plan-marshall:manage-solution-outline:manage-solution-outline (3 occurrences)
Component (suggested): plan-marshall:manage-solution-outline / phase-3-outline Q-Gate, phase-5-execute task reads (foreign bundle - route to plan-marshall lessons inbox)

## What happened

1. 2026-10-17T19:48:10Z, 3-outline Q-Gate:
   `deliverable-hashes --check --plan-id ... --phase 3-outline` -> exit 2
   `invalid_invocation / unknown_verb`; accepted verbs: exists, get-deliverable,
   get-field, get-module-context, list-deliverables, read, resolve-path, update,
   validate, write. Notably, later calls at 20:37:50Z and 20:42:41Z with the same
   verb `deliverable-hashes` SUCCEEDED - so the verb exists in some resolution
   path but was rejected by the executor's verb guard at 19:48. Either the
   executor mapping was stale for that dispatch or the verb is registered under
   a different shape; worth checking the executor's accepted-verb list against
   the script's argparse.
2. 2026-10-17T21:15:31Z and 22:33:33Z, 5-execute:
   `get-deliverable --plan-id ... --number 2` (and `--number 5`) -> exit 2
   `unknown_flag --number`; accepted: `--deliverable-number`, `--plan-id`.
   Same paraphrase repeated twice in one run; the retry with
   `--deliverable-number` succeeded both times.

## Candidate rule

`get-deliverable` takes `--deliverable-number`, never `--number`. Investigate the
`deliverable-hashes` verb-guard discrepancy (rejected once, accepted later).
