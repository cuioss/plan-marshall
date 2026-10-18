envelope_version=1
sender_type=orchestrator
sender_id=pm-mcp-core-m2-m4
epic=lessons-routing
kind=candidate-lesson
created=2026-10-18T10:23:52Z

component=plan-marshall:persona-plan-marshall-agent
category=anti-pattern
created=2026-10-18

# Argparse rejections across eight script notations in one plan

## Context

The plan retrospective of plan-20-job-runner counted 16 script failures in 8 distinct notations, all exit code 2 (argparse rejection before the script body ran):

| Notation | Subcommand | Subtype | Count |
|---|---|---|---|
| manage-architecture:architecture | search | invented_flag | 5 |
| manage-solution-outline:manage-solution-outline | deliverable-hashes | argparse_other | 3 |
| manage-findings:manage-findings | qgate | argparse_other | 2 |
| manage-tasks:manage-tasks | finalize-step | argparse_other | 2 |
| manage-logging:manage-logging | read | argparse_other | 1 |
| manage-change-ledger:manage-change-ledger | query | invented_flag (--status success --plan-id) | 1 |
| phase-6-finalize:review_support | validate | argparse_other | 1 |
| tools-integration-ci:ci | --plan-id (router flag read as the verb) | argparse_other | 1 |

The five architecture search rejections show the top-level usage, so the flags were not accepted at all; they come from leaves that were denied Grep and turned to architecture search (see candidate-lesson plan-20-job-runner-006 for the Grep-denial side; this message is the invocation side). The ci rejection is the router-scoped --plan-id signature; the change-ledger one passes flags query does not declare.

## Root cause

Leaves wrote the flag set from workflow prose or from a neighbouring verb instead of from the script's canonical-invocation block or --help. For manage-findings qgate and manage-solution-outline the stderr excerpt is empty, so the log does not record which argument was wrong.

## Proposed action

1. For the notations above, check that each consuming workflow quotes the canonical invocation verbatim (plugin-doctor manage-invocation-invalid / ARGUMENT_NAMING rules).
2. Make the script-execution log keep the argparse stderr line for exit code 2, so a retrospective can say which flag was invented (four of the eight clusters have an empty stderr_excerpt).
3. Add the architecture search flag set to the Grep-fallback guidance so a leaf that falls back gets the call right the first time.

## Evidence

- retrospective script-failure-analysis: total_failures 16, unique_failures 8 (log logs/script-execution.log)
