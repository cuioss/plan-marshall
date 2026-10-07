envelope_version=1
sender_type=plan
sender_id=implement-plan-165-close-orphan-defects
epic=test-quality
kind=candidate-lesson
created=2026-09-13T11:18:58Z

component=plan-marshall:tools-script-executor
category=anti-pattern

# Three distinct argparse/notation rejections in one plan run

## Context

Of the four unique script-call failures this plan recorded, three are caller-shape errors rather than script defects — the call never reached the script body, so the executor rejected it and the surrounding workflow had to recover:

1. `plan-marshall:manage-execution-manifest:manage_execution_manifest` — rejected as an invalid notation. The executor's own message diagnosed it: "The third part 'manage_execution_manifest' appears to be a subcommand, not a script name." The third segment must be the hyphenated on-disk script filename (`manage-execution-manifest`), not an underscored variant of it.
2. `plan-marshall:tools-integration-ci:ci pr edit` — `error: the following arguments are required: --plan-id`. This is the canonical signature-2/signature-4 confusion: on the `ci` router `--plan-id` is router-scoped for some verbs and subparser-required for others, and `pr edit` declares it on the subcommand.
3. `plan-marshall:automatic-review:review_completeness check` — argparse rejection (exit 2) against the `check` subcommand's declared flag set.

## Root cause

All three are instances of the documented "Never invent script subcommands" recurrence family: a plausible-looking notation or flag shape was written from surrounding prose rather than quoted verbatim from the executor mapping or a `--help` walk. The underscore/hyphen slip in (1) is particularly easy to make because Python module names in this repo ARE underscored while the notation's third segment tracks the filename.

## Proposed action

These are caller-discipline failures with an existing structural guard (the `ARGUMENT_NAMING_*` plugin-doctor cluster) that operates at edit time on documentation, not at call time on workflow bodies. Consider whether the executor's notation rejection — which already diagnoses the underscore case precisely and names the correct form — could be surfaced to the failing workflow as a retryable correction rather than only as an error, since the executor demonstrably knows the right answer at the moment it refuses. Worth noting that this retrospective run reproduced the same class itself: an invented `--field` flag on `manage-references read` was rejected with `unknown_flag`, and the rejection's `accepted: plan-id` list supplied the fix immediately.

## Evidence

- aspect: script_failure_analysis — `bug,script_internal_error,"plan-marshall:manage-execution-manifest:manage_execution_manifest","",1,"2026-09-12T23:27:58Z","Invalid notation ... The third part 'manage_execution_manifest' appears to be a subcommand, not a script name.",1`
- aspect: script_failure_analysis — `anti-pattern,missing_required_flag,"plan-marshall:tools-integration-ci:ci",--plan-id,2,"2026-09-13T00:29:51Z","ci.py pr edit: error: the following arguments are required: --plan-id",1`
- aspect: script_failure_analysis — `anti-pattern,argparse_other,"plan-marshall:automatic-review:review_completeness",check,2,"2026-09-13T09:04:53Z",...,1`
