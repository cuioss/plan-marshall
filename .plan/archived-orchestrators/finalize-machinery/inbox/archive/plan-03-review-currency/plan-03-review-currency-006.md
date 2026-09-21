envelope_version=1
sender_type=plan
sender_id=plan-03-review-currency
epic=finalize-machinery
kind=candidate-lesson
created=2026-09-17T18:06:27Z

component=plan-marshall:tools-integration-ci
category=anti-pattern
created=2026-09-17

# Invented script verbs and misplaced router flags cause argparse rejections in-run

Plan plan-03-review-currency hit repeated exit_code=2 argparse rejections across distinct notations: plan-marshall:manage-architecture:architecture (unrecognized positional path arg, run_script verb), plan-marshall:tools-integration-ci:ci (misplaced --plan-id after verb, invented list-comments verb, --pr flag name), plan-marshall:automatic-review:review_completeness (invented trigger-bot verb), plan-marshall:plan-retrospective:check-artifact-consistency (undeclared --output-file).

## Pattern

Plausible-sounding verbs and flags extrapolated from workflow prose bypass the script body and corrupt downstream behaviour. Each case resolved by quoting the subcommand and flag names verbatim from the executor mapping or --help output.

## Candidate rule for orchestrator judgement

Never invent script subcommands or flags; when in doubt invoke with --help first. Respect per-script --plan-id placement (router-consumed before verb vs subcommand-scoped after verb) and never append --plan-id by rote.

## Evidence

signal_script_failure_clusters_count>=1; work.log [ERROR] script_failure lines for the notations above (argparse_rejection failure_kind).
