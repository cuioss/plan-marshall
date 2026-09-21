envelope_version=1
sender_type=plan
sender_id=ledger-joins
epic=quality-aspect
kind=candidate-lesson
created=2026-09-20T07:29:24Z

component=plan-marshall:tools-script-executor
category=anti-pattern
created=2026-09-20

# Script-failure clusters led by argparse rejections from invented subcommands

## Observation

Plan ledger-joins (PR #1545, merged) produced 8 distinct failing script
notations across the [FAILED], [ERROR] script_failure, and
voluntary_checkpoint-to-error marker classes (union-deduped by notation).
The clusters are led by argparse rejections: invented or paraphrased
manage-* subcommands and flags that do not exist in the script's argparse
choices (exit_code 2), including verb-scoped --plan-id placement errors.

## Signal context

- Source: dispatcher-forwarded signal_script_failure_clusters_count = 8
- Candidate classification is deferred to the orchestrator-side pickup; the
  plan transmits this record unjudged as kind: candidate-lesson for the
  quality-aspect epic

## Provisional corrective direction (for orchestrator judgement)

Quote subcommand and flag names verbatim from the executor mappings or the
script's --help output; never extrapolate plausible-sounding verbs. When in
doubt, invoke the script with --help first. Each cluster's notation, the
rejected token, and the canonical replacement belong in the orchestrator's
recurrence judgement.
