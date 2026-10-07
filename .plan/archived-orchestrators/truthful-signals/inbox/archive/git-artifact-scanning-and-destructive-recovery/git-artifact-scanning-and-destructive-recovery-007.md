envelope_version=1
sender_type=plan
sender_id=git-artifact-scanning-and-destructive-recovery
epic=truthful-signals
kind=candidate-lesson
created=2026-08-31T08:03:37Z

component=plan-marshall:tools-script-executor
category=improvement
created=2026-08-31
bundle=plan-marshall
confidence=high
source_plan=git-artifact-scanning-and-destructive-recovery

# Emit the failing verb's live --help on any argparse exit-2 from the executor

## Context

This run made 1,887 script calls and took **26 argparse rejections across 12 distinct scripts** (15 unique signatures). Every one of them was recoverable deterministically from the script's own `--help`, and every one cost at least one wasted LLM turn.

The distribution:

| Script | Rejections |
|---|---|
| `manage-solution-outline get-deliverable` | 5 |
| `manage-findings qgate` | 4 |
| `tools-integration-ci:ci` (all forms) | 6 |
| `automatic-review:review_completeness check` | 3 |
| `manage-status`, `manage-tasks`, `git-workflow`, `github_pr`, `manage-references`, `architecture`, `merge_lock`, `manage-config` | 1 each |

The `ci.py` `--plan-id` trap is the sharpest case, because it **fired in both directions in the same run**:

- `--plan-id` placed AFTER a router-flag verb → `unrecognized arguments`, and the router DOES emit a corrective hint ("note: `--plan-id` is a top-level flag and belongs BEFORE...").
- `--plan-id` placed BEFORE a body-consumer verb whose subparser declares its own required `--plan-id` → `the following arguments are required`, with **no hint at all**. The router swallowed the pre-verb flag and the subparser then rejected the call for a missing required argument.

One direction is self-correcting; its mirror is not.

## Root cause

An argparse exit-2 is a machine-readable failure with a machine-readable remedy sitting one `--help` call away, and the executor discards it. The model then re-derives the correct surface from prose, which is both slower and less reliable than reading the parser.

## Proposed action

1. **Executor-level.** When a script exits non-zero with an argparse signature — `invalid choice:`, `unrecognized arguments:`, `the following arguments are required:` — have `.plan/execute-script.py` append the failing verb's live `--help` surface to stderr. The router's existing one-off `ci --plan-id` hint is the proof of concept; generalising it would have covered all 26 rejections in this run.
2. **`ci.py`-specific.** Add the symmetric subparser-side hint — "note: this verb declares its own `--plan-id` AFTER the verb" — so both placement errors are equally self-correcting. Today the trap is asymmetric, which teaches half a rule.

Both are low complexity: the first is one branch in the executor's error path, the second is one message string.

## Evidence

- aspect: script_failure_analysis — `total_failures: 26`, `unique_failures: 15`, 12 distinct scripts, three argparse subtypes (`invented_flag`, `invented_subcommand`, `missing_required_flag`) plus `argparse_other`
- aspect: llm_to_script_opportunities — repetition_count 26, complexity low
- The `ci.py` both-directions evidence sits in two adjacent log rows: `2026-08-30T19:20:50Z` (post-verb, hinted) and `2026-08-31T07:44:54Z` (pre-verb, unhinted)
