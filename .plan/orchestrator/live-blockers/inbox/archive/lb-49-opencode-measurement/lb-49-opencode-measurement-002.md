envelope_version=1
sender_type=plan
sender_id=lb-49-opencode-measurement
epic=live-blockers
kind=candidate-lesson
created=2026-10-22T11:22:23Z

# Declare every flag a workflow passes, or stop passing it

## Context

The plan's `script-execution.log` recorded 40 non-zero exits across 20 unique
signatures. Sixteen of them were argparse rejections at the flag level, and the
same shape recurred on five different scripts within one plan:
`manage-change-ledger query --plan-id` (6 occurrences),
`manage-tasks get` (7), `manage-logging read` (3),
`platform-runtime harness bash-timeout-ceiling --plan-id` (3),
`manage-architecture resolve ... --plan-id` (2), plus
`manage-adr scan --plan-id` and `manage-run-config` variants.

Every rejection cost a round trip and, in three cases, the calling step fell
back to a weaker evidence path rather than retrying with the right shape.

## Root cause

`--plan-id` is treated as universal routing state, but each script declares it
in a different place — router-level on `ci`, subcommand-level on
`manage-config` / `manage-architecture`, and not at all on
`manage-change-ledger`, `manage-logging read` or `manage-tasks get`. Workflow
prose that says "forward `--plan-id` to every script call" is therefore wrong
as written, and an agent quoting the prose verbatim produces a rejection that
the script's own parser could have predicted.

## Proposed action

Make the mismatch impossible to reach at runtime: give
`tools-script-executor`'s `execute-script.py` a validation mode that builds the
target script's real argparse parser and parses the requested argv without
executing it, returning the accept-set on rejection. Callers that want the
strict form use it before an expensive or fallback-triggering call. In parallel,
sweep the workflow docs for `--plan-id` on the scripts whose parser does not
declare it and delete the flag from those call sites.

## Evidence

- aspect: script_failure_analysis — 40 failures / 20 unique signatures; 16 argparse-flag rejections
- aspect: llm_to_script_opportunities — candidate "discover each manage-* invocation's accepted flags before calling it", repetition_count 20
- aspect: log_analysis — `script_cost_rollup` shows 3051 calls, so the failure rate is a rate, not a one-off
