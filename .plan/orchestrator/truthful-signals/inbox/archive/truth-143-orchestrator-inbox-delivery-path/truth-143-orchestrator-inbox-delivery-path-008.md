envelope_version=1
sender_type=plan
sender_id=truth-143-orchestrator-inbox-delivery-path
epic=truthful-signals
kind=candidate-lesson
created=2026-09-20T08:18:46Z

# Add a pre-flight invocation validator to stop systemic argparse-surface guessing

component: plan-marshall:tools-script-executor
category: improvement
confidence: medium

## Context

`script-failure-analysis` found 41 script-call failures on this plan across 18 unique signatures. Sixteen of the eighteen are argparse rejections (`exit_code: 2`), spread across 14 distinct scripts — `manage-findings`, `manage-execution-manifest`, `manage-solution-outline`, `manage-logging`, `manage-change-ledger`, `orchestrator`, `ci_verify`, `manage-tasks`, `architecture`, `ci`, `manage-metrics`, `manage-status`, `manage-files`, `build_server`. Two are script-internal errors and one is a notation error (`plan-marshall:manage-status:manage_status`, underscore for hyphen in the script-name segment).

The distribution is not one bad script. The two worst verbs account for 16 rejections between them — `manage-findings qgate` (8) and `manage-solution-outline get-deliverable` (8) — and the remaining twelve scripts contribute one to four each.

## Root cause

Each rejection is an invocation shape reconstructed from surrounding prose rather than read off the script's declared argparse surface. The existing mitigations are all *post hoc* or *authoring-time*: the `ARGUMENT_NAMING_*` plugin-doctor rule cluster guards the declaration side, `recipe-fix-argparse-rejection` helps after a rejection, and the canonical-forms table in `argument-naming.md` documents the shapes for the scripts it covers. None of them intervenes between an agent composing a call and the call failing.

The cost is not only the failed call. Each rejection is followed by a re-read and a retry inside a dispatched envelope, so the 41 failures represent considerably more than 41 wasted round-trips on a plan whose finalize phase already out-spent its execute phase.

## Proposed action

Add a pre-flight verb to `tools-script-executor` that takes a proposed `{notation} {verb} {flags...}` invocation, resolves the target script's live `--help` accept-set (the same walk `manage-invocation-invalid` already performs), and returns either `valid` or the nearest canonical form with the specific mismatch named. One lookup replaces the reject-reread-retry cycle, and it works for every script rather than only those with a canonical-forms table row.

Two lower-cost complements, worth doing regardless: publish canonical-invocation blocks for the two worst verbs (`manage-findings qgate`, `manage-solution-outline get-deliverable`), which alone would have removed 16 of the 41 rejections on this plan.

## Evidence

- aspect: script_failure_analysis — `total_failures: 41`, `unique_failures: 18`, 16 of 18 classified `argparse_other` or `invented_flag`
- aspect: script_failure_analysis — `manage-findings qgate` occurrence_count 8; `manage-solution-outline get-deliverable` occurrence_count 8
- aspect: script_failure_analysis — one notation error, `plan-marshall:manage-status:manage_status`, rejected with an explicit "third part appears to be a subcommand" message
- aspect: llm_to_script_opportunities — this is the highest-repetition candidate surfaced on the plan
