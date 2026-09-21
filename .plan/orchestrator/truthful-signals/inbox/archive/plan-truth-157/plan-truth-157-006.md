envelope_version=1
sender_type=plan
sender_id=plan-truth-157
epic=truthful-signals
kind=candidate-lesson
created=2026-09-14T20:51:04Z

# Runtime argparse rejections recur despite all five signatures being documented

component: plan-marshall:persona-plan-marshall-agent
category: improvement
confidence: medium
source_plan: plan-truth-157
source_aspects: script_failure_analysis

## Context

This plan produced 6 argparse rejections across 5 unique call shapes:

| Component | Verb | Subtype | Count |
|-----------|------|---------|-------|
| `plan-marshall:manage-execution-manifest` | `read` | argparse_other | 1 |
| `plan-marshall:tools-integration-ci:ci` | `--plan-id` | argparse_other | 1 |
| `plan-marshall:tools-integration-ci:ci` | `pr prepare-body` | missing_required_flag | 1 |
| `plan-marshall:manage-findings` | `list` | argparse_other | 2 |
| `plan-marshall:manage-architecture` | `search` | invented_flag | 1 |

Two of them are the documented mirror pair: a `ci pr prepare-body` call that omitted its verb-scoped
`--plan-id` (the subparser rejected it as a missing required argument), and a separate `ci --plan-id`
placement rejection. The rule set documents both directions as signatures 2 and 4 and explicitly warns that
they prescribe opposite moves on different surfaces.

## Root cause

This entry deliberately does NOT restate those five signatures. They are already documented at their single
home in `agent-behavior-rules.md` § "Never invent script subcommands — recurrence signatures", and
restating them here would seed the corpus with a second copy of a rule that already exists — the failure mode
this epic exists to remove.

The observation is a different one: a fully-documented rule, plus edit-time structural enforcement (the
`ARGUMENT_NAMING_*` plugin-doctor cluster, which checks *authored documents*), still permitted 6 runtime
invocations to fail in one plan. The enforcement and the failure are on different surfaces — the cluster
validates what a doc says, while the failures are what an agent typed — so nothing reaches the agent between
reading the rule and issuing the call.

## Proposed action

None proposed here. This is recorded as an observation with its count for the orchestrator to weigh against
the cross-plan rate, which only the orchestrator can see.

Deliberately NOT proposed: a runtime guard. This project's standing preference is to fix call sites rather
than add runtime guards around them, and a guard would also be the third copy of a rule that already has
two homes. If the cross-plan rate justifies action, the question worth asking is which call sites recur —
not how to intercept them.

## Evidence

- aspect: script_failure_analysis — `total_failures: 6`, `unique_failures: 5`, with the per-component
  breakdown above and `work_log_unrecognized_lines: 0`
- The `ci pr prepare-body` rejection carries the full stderr: `ci.py pr prepare-body: error: the following
  arguments are required: --plan-id`
- Signatures 2 and 4 in `agent-behavior-rules.md` document both placement directions for exactly these two
  surfaces; the failures are instances of documented shapes, not of undocumented ones
